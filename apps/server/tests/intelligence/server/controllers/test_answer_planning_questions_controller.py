from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from typing import TYPE_CHECKING

from shifu.intelligence.core.domain.enums import (
    PlanningQuestionKind,
    PlanningSessionStatus,
)
from shifu.intelligence.core.domain.structures import (
    PlanningOperationResult,
    PlanningOption,
    PlanningQuestion,
    PlanningQuestionBatch,
)
from tests.intelligence.server.controllers.planning_test_support import (
    interviewing_session,
    planning_events,
    sessions_of,
    started_session,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from shifu.intelligence.core.domain.entities import PlanningSession

    from tests.fixtures.postgres_fixture import PostgresDatabase

_VALID = {
    'batch_id': 'batch-1',
    'answers': [{'question_id': 'q1', 'option_ids': ['o2']}],
}


def _interviewing_with_other() -> PlanningSession:
    session = started_session()
    operation = session.operation
    assert operation is not None
    question = PlanningQuestion(
        id='q1',
        text='O que você quer construir?',
        kind=PlanningQuestionKind.MULTIPLE,
        options=(
            PlanningOption(id='o1', text='Sites'),
            PlanningOption(id='o2', text='APIs'),
            PlanningOption.other(),
        ),
    )
    batch = PlanningQuestionBatch(id='batch-1', questions=(question,))
    assert session.complete(
        operation.id, 1, PlanningOperationResult.for_batch(batch), datetime.now(UTC)
    )
    return session


class TestAnswerPlanningQuestionsController:
    def test_should_accept_a_complete_batch_and_request_the_next_operation(
        self, planning_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session = interviewing_session()
        sessions_of(planning_client).add(session)

        response = planning_client.post(
            f'/intelligence/planning-sessions/{session.id}/answers', json=_VALID
        )

        assert response.status_code == 202, response.text
        body = response.json()
        assert body['status'] == 'processing'
        assert body['operation']['kind'] == 'answer'
        assert body['batch'] is None
        assert body['answered_batch_count'] == 1
        events = planning_events(postgres_database.engine)
        assert len(events) == 1
        assert events[0].payload['planning_id'] == session.id
        assert events[0].payload['generation'] == 1
        stored = sessions_of(planning_client).find_by_id(session.id)
        assert stored is not None
        assert stored.answered_batches[0].items[0].selected_texts == ('APIs',)

    def test_should_accept_an_open_answer_with_the_learner_text(
        self, planning_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session = _interviewing_with_other()
        sessions_of(planning_client).add(session)

        response = planning_client.post(
            f'/intelligence/planning-sessions/{session.id}/answers',
            json={
                'batch_id': 'batch-1',
                'answers': [
                    {
                        'question_id': 'q1',
                        'option_ids': ['o2', 'outro'],
                        'other_text': 'planilhas no Excel',
                    }
                ],
            },
        )

        assert response.status_code == 202, response.text
        assert len(planning_events(postgres_database.engine)) == 1
        stored = sessions_of(planning_client).find_by_id(session.id)
        assert stored is not None
        item = stored.answered_batches[0].items[0]
        assert item.answer_texts == ('APIs', 'planilhas no Excel')

    def test_should_reject_an_open_answer_without_text_or_over_the_limit(
        self, planning_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session = _interviewing_with_other()
        sessions_of(planning_client).add(session)

        def answer(other_text: str | None) -> int:
            return planning_client.post(
                f'/intelligence/planning-sessions/{session.id}/answers',
                json={
                    'batch_id': 'batch-1',
                    'answers': [
                        {
                            'question_id': 'q1',
                            'option_ids': ['outro'],
                            'other_text': other_text,
                        }
                    ],
                },
            ).status_code

        assert answer(None) == 400
        assert answer('x' * 201) == 422
        assert planning_events(postgres_database.engine) == []

    def test_should_reject_an_invalid_selection_without_side_effects(
        self, planning_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session = interviewing_session()
        sessions_of(planning_client).add(session)

        response = planning_client.post(
            f'/intelligence/planning-sessions/{session.id}/answers',
            json={
                'batch_id': 'batch-1',
                'answers': [{'question_id': 'q1', 'option_ids': ['nao-sei', 'o1']}],
            },
        )

        assert response.status_code == 400
        assert response.json() == {
            'code': 'validation_error',
            'message': 'Perguntas de escolha única aceitam exatamente uma alternativa.',
        }
        assert planning_events(postgres_database.engine) == []
        stored = sessions_of(planning_client).find_by_id(session.id)
        assert stored is not None
        assert stored.status is PlanningSessionStatus.INTERVIEW

    def test_should_refuse_answers_while_an_operation_runs(
        self, planning_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session = started_session()
        sessions_of(planning_client).add(session)

        response = planning_client.post(
            f'/intelligence/planning-sessions/{session.id}/answers', json=_VALID
        )

        assert response.status_code == 409
        assert response.json() == {
            'code': 'conflict',
            'message': 'Já existe uma operação em andamento neste planejamento.',
        }
        assert planning_events(postgres_database.engine) == []

    def test_should_start_exactly_one_operation_for_concurrent_submissions(
        self, planning_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session = interviewing_session()
        sessions_of(planning_client).add(session)
        barrier = Barrier(2)

        def submit(_: int) -> int:
            barrier.wait(timeout=10)
            return planning_client.post(
                f'/intelligence/planning-sessions/{session.id}/answers', json=_VALID
            ).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = sorted(pool.map(submit, range(2)))

        assert statuses == [202, 409]
        assert len(planning_events(postgres_database.engine)) == 1

    def test_should_hide_a_foreign_planning(self, planning_client: TestClient) -> None:
        session = interviewing_session(account_id='01JACCOUNT00000000000OTHER')
        sessions_of(planning_client).add(session)

        response = planning_client.post(
            f'/intelligence/planning-sessions/{session.id}/answers', json=_VALID
        )

        assert response.status_code == 404
