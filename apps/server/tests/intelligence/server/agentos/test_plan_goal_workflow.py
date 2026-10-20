from __future__ import annotations

import os
from threading import Event
from time import monotonic, sleep
from typing import TYPE_CHECKING, cast

import pytest

from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.curriculum.providers import DatabaseCurriculumCatalogProvider
from shifu.intelligence.ai.data.planner_resources import PlannerResources
from shifu.intelligence.core.domain.enums import (
    PlanningOperationStage,
    PlanningSessionStatus,
)
from shifu.intelligence.database.planning_embeddings_database_repository import (
    PlanningEmbeddingsDatabaseRepository,
)
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.intelligence.prepare_planning_indexes import prepare_indexes
from shifu.intelligence.providers.embeddings.sentence_transformers.sentence_transformers_embeddings_provider import (
    SentenceTransformersEmbeddingsProvider,
)
from shifu.intelligence.providers.planning.text_preprocessing.spacy.spacy_planning_text_preprocessor_provider import (
    SpacyPlanningTextPreprocessorProvider,
)
from shifu.shared.database.seed_data import build_development_seed

if TYPE_CHECKING:
    from fastapi import FastAPI

    from shifu.intelligence.core.interfaces import PlanningSessionsRepository
    from tests.fixtures.agentos_fixture import RegisteredAgentOSFixture
    from tests.fixtures.postgres_fixture import PostgresDatabase

pytestmark = pytest.mark.skipif(
    os.environ.get('SHIFU_RUN_REAL_AGENTOS_TESTS') != '1',
    reason='Set SHIFU_RUN_REAL_AGENTOS_TESTS=1 for registered AgentOS tests',
)

_TERMINAL = {
    'interview',
    'proposal',
    'out-of-scope',
    'unsupported',
    'validation-failed',
    'failed',
}
_INVALID_DRAFT: dict[str, object] = {
    'supported': True,
    'title': 'Aprender web',
    'description': 'Duplicada.',
    'skills': [
        {'skill_id': 'skill-ghost', 'justification': 'Não existe.'},
        {'skill_id': 'skill-ghost', 'justification': 'Repetida.'},
    ],
}
_CLARIFICATION: dict[str, object] = {
    'needs_clarification': True,
    'questions': [
        {
            'text': 'O que você quer construir primeiro?',
            'kind': 'single',
            'options': ['Páginas e layout', 'Interatividade', 'Outro'],
            'allow_unknown': True,
        }
    ],
}


@pytest.fixture
def planner_runtime(
    agentos_fixture: RegisteredAgentOSFixture, postgres_database: PostgresDatabase
) -> RegisteredAgentOSFixture:
    """Seed the authorized Skills and prepare the Planner index behind the running app."""
    seed = build_development_seed()
    curriculum = SqlalchemyCurriculumDatabase(postgres_database.engine)
    with curriculum.transaction() as repositories:
        repositories.skills.add_many(list(seed.skills))
        repositories.skill_foundations.add_many(list(seed.skill_foundations))
    resources = PlannerResources()
    prepare_indexes(
        SentenceTransformersEmbeddingsProvider(),
        PlanningEmbeddingsDatabaseRepository(
            SqlalchemyIntelligenceDatabase(engine=postgres_database.engine)
        ),
        DatabaseCurriculumCatalogProvider(curriculum),
        resources,
        SpacyPlanningTextPreprocessorProvider(resources.manifest.negation),
    )
    return agentos_fixture


def _sessions(fixture: RegisteredAgentOSFixture) -> PlanningSessionsRepository:
    app = cast('FastAPI', fixture.client.app)
    return cast('PlanningSessionsRepository', app.state.planning_sessions_repository)


def _start(fixture: RegisteredAgentOSFixture, intent: str) -> str:
    response = fixture.client.post(
        '/intelligence/planning-sessions', json={'initial_intent': intent}
    )
    assert response.status_code == 201, response.text
    return cast('str', response.json()['id'])


def _wait(
    fixture: RegisteredAgentOSFixture, planning_id: str, *, generation: int = 1
) -> dict[str, object]:
    deadline = monotonic() + 60
    while monotonic() < deadline:
        response = fixture.client.get(f'/intelligence/planning-sessions/{planning_id}')
        assert response.status_code == 200, response.text
        body = cast('dict[str, object]', response.json())
        if body['status'] in _TERMINAL and body['generation'] == generation:
            return body
        sleep(0.5)
    pytest.fail('Registered planning workflow did not reach a terminal state')


class TestPlanGoalWorkflow:
    def test_should_compose_a_proposal_directly_for_a_sufficient_intent(
        self, planner_runtime: RegisteredAgentOSFixture
    ) -> None:
        planning_id = _start(
            planner_runtime, 'Quero aprender a construir sites com HTML, CSS e React'
        )

        body = _wait(planner_runtime, planning_id)

        assert body['status'] == 'proposal'
        assert body['consulted_curriculum'] is True
        proposal = cast('dict[str, object]', body['proposal'])
        skills = cast('list[dict[str, object]]', proposal['skills'])
        names = {skill['name'] for skill in skills}
        assert names <= {'React', 'JavaScript essencial', 'HTML e CSS'}
        assert len(names) == len(skills)
        relations = cast('list[dict[str, object]]', proposal['relations'])
        assert relations, 'direct Curriculum relations among proposed Skills'
        assert all(
            {relation['skill_id'], relation['foundation_skill_id']}
            <= {skill['skill_id'] for skill in skills}
            for relation in relations
        )
        assert body['message'] is None
        assert len(planner_runtime.decisions.requests) == 1
        # Only the intent, the answers and the candidate texts reach the model.
        assert planner_runtime.model_transport.planner_requests
        assert all(
            set(request)
            <= {'intent', 'answers', 'candidates', 'remaining_batches', 'problems'}
            for request in planner_runtime.model_transport.planner_requests
        )
        assert len(planner_runtime.model_transport.planner_requests) == 2

    def test_should_ask_a_batch_and_compose_after_the_answers(
        self, planner_runtime: RegisteredAgentOSFixture
    ) -> None:
        planner_runtime.model_transport.planner_interview_outputs = [
            dict(_CLARIFICATION)
        ]
        planning_id = _start(planner_runtime, 'Quero aprender a fazer sites')

        interview = _wait(planner_runtime, planning_id)

        assert interview['status'] == 'interview'
        batch = cast('dict[str, object]', interview['batch'])
        questions = cast('list[dict[str, object]]', batch['questions'])
        assert len(questions) == 1
        options = cast('list[dict[str, object]]', questions[0]['options'])
        assert [option['text'] for option in options] == [
            'Páginas e layout',
            'Interatividade',
            'Não sei',
        ]
        assert options[-1]['exclusive'] is True
        answered = planner_runtime.client.post(
            f'/intelligence/planning-sessions/{planning_id}/answers',
            json={
                'batch_id': batch['id'],
                'answers': [
                    {
                        'question_id': questions[0]['id'],
                        'option_ids': [options[1]['id']],
                    }
                ],
            },
        )
        assert answered.status_code == 202, answered.text

        final = _wait(planner_runtime, planning_id)

        assert final['status'] == 'proposal'
        assert final['answered_batch_count'] == 1
        assert final['batch'] is None
        requests = planner_runtime.model_transport.planner_requests
        answers = cast('list[dict[str, object]]', requests[-1]['answers'])
        assert answers == [
            {
                'question': 'O que você quer construir primeiro?',
                'kind': 'single',
                'selected': ['Interatividade'],
            }
        ]
        assert len(planner_runtime.decisions.requests) == 1

    def test_should_end_out_of_scope_without_calling_the_model(
        self, planner_runtime: RegisteredAgentOSFixture
    ) -> None:
        planner_runtime.decisions.kind = 'out-of-scope'
        planning_id = _start(planner_runtime, 'Quero comprar um notebook barato')

        body = _wait(planner_runtime, planning_id)

        assert body['status'] == 'out-of-scope'
        assert body['message']
        assert body['batch'] is None
        assert body['proposal'] is None
        assert body['consulted_curriculum'] is False
        assert planner_runtime.model_transport.planner_requests == []

    def test_should_report_unsupported_when_the_composer_declines(
        self, planner_runtime: RegisteredAgentOSFixture
    ) -> None:
        planner_runtime.model_transport.planner_proposal_outputs = [
            {'supported': False, 'title': '', 'description': '', 'skills': []}
        ]
        planning_id = _start(planner_runtime, 'Quero aprender a tocar violão')

        body = _wait(planner_runtime, planning_id)

        assert body['status'] == 'unsupported'
        assert body['message']
        assert body['proposal'] is None

    def test_should_correct_an_invalid_draft_before_exposing_a_proposal(
        self, planner_runtime: RegisteredAgentOSFixture
    ) -> None:
        planner_runtime.model_transport.planner_proposal_outputs = [
            dict(_INVALID_DRAFT)
        ]
        planning_id = _start(planner_runtime, 'Quero aprender React')

        body = _wait(planner_runtime, planning_id)

        assert body['status'] == 'proposal'
        proposal_requests = [
            request
            for request in planner_runtime.model_transport.planner_requests
            if 'problems' in request
        ]
        assert len(proposal_requests) == 2
        assert proposal_requests[0]['problems'] == []
        problems = cast('list[str]', proposal_requests[1]['problems'])
        assert any('não existe' in problem for problem in problems)

    def test_should_fail_validation_after_four_invalid_drafts(
        self, planner_runtime: RegisteredAgentOSFixture
    ) -> None:
        planner_runtime.model_transport.planner_proposal_outputs = [
            dict(_INVALID_DRAFT) for _ in range(4)
        ]
        planning_id = _start(planner_runtime, 'Quero aprender React')

        body = _wait(planner_runtime, planning_id)

        assert body['status'] == 'validation-failed'
        assert body['failure_code'] == 'validation_exhausted'
        assert body['proposal'] is None
        assert (
            len(
                [
                    request
                    for request in planner_runtime.model_transport.planner_requests
                    if 'problems' in request
                ]
            )
            == 4
        )

    def test_should_recover_from_a_classification_failure_through_retry(
        self, planner_runtime: RegisteredAgentOSFixture
    ) -> None:
        planner_runtime.decisions.fail_next = 3
        planning_id = _start(planner_runtime, 'Quero aprender React')

        failed = _wait(planner_runtime, planning_id)

        assert failed['status'] == 'failed'
        assert failed['failure_code'] == 'service_unavailable'
        assert failed['intent'] == 'Quero aprender React'
        retried = planner_runtime.client.post(
            f'/intelligence/planning-sessions/{planning_id}/retry'
        )
        assert retried.status_code == 202, retried.text

        recovered = _wait(planner_runtime, planning_id)

        assert recovered['status'] == 'proposal'

    def test_should_discard_a_late_result_after_cancel(
        self, planner_runtime: RegisteredAgentOSFixture
    ) -> None:
        gate = Event()
        planner_runtime.model_transport.planner_gate = gate
        planner_runtime.model_transport.planner_block_first = 1
        planning_id = _start(planner_runtime, 'Quero aprender React')
        deadline = monotonic() + 30
        while (
            not planner_runtime.model_transport.planner_requests
            and monotonic() < deadline
        ):
            sleep(0.2)
        assert planner_runtime.model_transport.planner_requests
        # The workflow reported its stage before blocking on the interview model;
        # the repository is read directly so the short test timeout cannot expire it.
        in_flight = _sessions(planner_runtime).find_by_id(planning_id)
        assert in_flight is not None
        assert in_flight.status is PlanningSessionStatus.PROCESSING
        assert in_flight.operation is not None
        assert in_flight.operation.stage is PlanningOperationStage.INTERVIEWING

        cancelled = planner_runtime.client.delete(
            f'/intelligence/planning-sessions/{planning_id}'
        )
        assert cancelled.status_code == 204
        gate.set()
        sleep(3)

        assert _sessions(planner_runtime).find_by_id(planning_id) is None
        detail = planner_runtime.client.get(
            f'/intelligence/planning-sessions/{planning_id}'
        )
        assert detail.status_code == 404

    def test_should_discard_a_late_result_of_a_restarted_generation(
        self, planner_runtime: RegisteredAgentOSFixture
    ) -> None:
        gate = Event()
        planner_runtime.model_transport.planner_gate = gate
        planner_runtime.model_transport.planner_block_first = 1
        planner_runtime.model_transport.planner_interview_outputs = [
            dict(_CLARIFICATION)
        ]
        planning_id = _start(planner_runtime, 'Quero aprender a fazer sites')
        timed_out = None
        # The 10 s operation timeout is observed through GET; slow runners need slack.
        deadline = monotonic() + 80
        while monotonic() < deadline:
            response = planner_runtime.client.get(
                f'/intelligence/planning-sessions/{planning_id}'
            )
            assert response.status_code == 200
            if response.json()['status'] == 'failed':
                timed_out = cast('dict[str, object]', response.json())
                break
            sleep(1)
        assert timed_out is not None
        assert timed_out['failure_code'] == 'operation_timeout'

        restarted = planner_runtime.client.post(
            f'/intelligence/planning-sessions/{planning_id}/restart',
            json={'initial_intent': 'Quero aprender React'},
        )
        assert restarted.status_code == 202, restarted.text
        gate.set()
        final = _wait(planner_runtime, planning_id, generation=2)

        assert final['status'] == 'proposal'
        assert final['generation'] == 2
        assert final['answered_batch_count'] == 0
        assert final['batch'] is None
