from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

import pytest
from sqlalchemy import text

from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.intelligence.core.domain.structures import (
    PlanningOperationResult,
    PlanningProposal,
    PlanningProposalSkill,
)
from shifu.shared.database.seed_data import (
    SEED_ADAPTIVE_LAB_SKILL_ID,
    SEED_ADAPTIVE_SKILL_ID,
    SEED_GRAPH_HTML_CSS_SKILL_ID,
    build_development_seed,
)
from tests.intelligence.server.controllers.conftest import MENTOR_ACCOUNT
from tests.intelligence.server.controllers.planning_test_support import (
    interviewing_session,
    sessions_of,
    started_session,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from httpx import Response

    from shifu.intelligence.core.domain.entities import PlanningSession

    from tests.fixtures.postgres_fixture import PostgresDatabase

CONFIRMATION_KEY = '3f0c2b9e-8d1a-4c57-9b2e-6a1d4f8c0e21'
TITLE = 'Automatizar tarefas do dia a dia com Python'
DESCRIPTION = (
    'Quero parar de fazer planilha na mão e escrever scripts que resolvam isso.'
)


def _seed_curriculum(database: PostgresDatabase) -> None:
    seed = build_development_seed()
    curriculum_database = SqlalchemyCurriculumDatabase(database.engine)
    with curriculum_database.transaction() as repositories:
        repositories.skills.add_many(list(seed.skills))
        repositories.skill_foundations.add_many(list(seed.skill_foundations))
        repositories.competencies.add_many(list(seed.competencies))
        repositories.concepts.add_many(list(seed.concepts))
        repositories.materials.add_many(list(seed.materials))
        repositories.activities.add_many(list(seed.activities))
        repositories.curriculum_sequences.add_many(list(seed.curriculum_sequences))


def _proposed_session(skill_ids: tuple[str, ...]) -> PlanningSession:
    session = started_session()
    operation = session.operation
    assert operation is not None
    proposal = PlanningProposal(
        title='Proposta original',
        description='Descrição original da proposta.',
        skills=tuple(
            PlanningProposalSkill(
                skill_id=skill_id,
                name=f'Habilidade {index}',
                justification=f'Justificativa {index} da proposta.',
            )
            for index, skill_id in enumerate(skill_ids, start=1)
        ),
    )
    assert session.complete(
        operation.id,
        1,
        PlanningOperationResult.for_proposal(proposal),
        datetime.now(UTC),
    )
    return session


def _confirm(
    client: TestClient,
    planning_id: str,
    *,
    key: str = CONFIRMATION_KEY,
    title: str = TITLE,
    description: str = DESCRIPTION,
) -> Response:
    return cast(
        'Response',
        client.post(
            f'/intelligence/planning-sessions/{planning_id}/confirm',
            json={'confirmation_key': key, 'title': title, 'description': description},
        ),
    )


def _learning_rows(database: PostgresDatabase, goal_id: str) -> dict[str, object]:
    with database.engine.connect() as connection:
        goal = connection.execute(
            text(
                'SELECT title, description, account_id FROM learning_goals WHERE id = :id'
            ),
            {'id': goal_id},
        ).one()
        experiences = connection.execute(
            text(
                'SELECT skill_id, inclusion_reason, status FROM learning_skill_experiences'
                ' WHERE goal_id = :id ORDER BY created_at, skill_id'
            ),
            {'id': goal_id},
        ).all()
        progresses = connection.execute(
            text(
                'SELECT COUNT(*) FROM learning_competency_progresses WHERE'
                ' skill_experience_id IN (SELECT id FROM learning_skill_experiences'
                ' WHERE goal_id = :id)'
            ),
            {'id': goal_id},
        ).scalar_one()
        confirmations = connection.execute(
            text(
                'SELECT planning_id, goal_id FROM learning_goal_confirmations'
                ' WHERE account_id = :account AND confirmation_key = :key'
            ),
            {'account': MENTOR_ACCOUNT.account_id, 'key': CONFIRMATION_KEY},
        ).all()
    return {
        'goal': tuple(goal),
        'experiences': [tuple(row) for row in experiences],
        'progresses': int(cast('int', progresses)),
        'confirmations': [tuple(row) for row in confirmations],
    }


def _goal_count(database: PostgresDatabase) -> int:
    with database.engine.connect() as connection:
        return int(
            connection.execute(text('SELECT COUNT(*) FROM learning_goals')).scalar_one()
        )


@pytest.fixture(autouse=True)
def seeded_curriculum(postgres_database: PostgresDatabase) -> None:
    _seed_curriculum(postgres_database)


class TestConfirmPlanningController:
    def test_should_create_the_goal_with_justifications_and_end_the_planning(
        self, planning_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session = _proposed_session(
            (SEED_ADAPTIVE_SKILL_ID, SEED_ADAPTIVE_LAB_SKILL_ID)
        )
        sessions_of(planning_client).add(session)

        response = _confirm(planning_client, session.id)

        assert response.status_code == 200, response.text
        body = response.json()
        assert body['replayed'] is False
        assert response.headers['cache-control'] == 'private, no-store'
        rows = _learning_rows(postgres_database, body['goal_id'])
        assert rows['goal'] == (TITLE, DESCRIPTION, MENTOR_ACCOUNT.account_id)
        assert rows['experiences'] == [
            (SEED_ADAPTIVE_SKILL_ID, 'Justificativa 1 da proposta.', 'not-started'),
            (SEED_ADAPTIVE_LAB_SKILL_ID, 'Justificativa 2 da proposta.', 'not-started'),
        ]
        assert cast('int', rows['progresses']) > 0
        assert rows['confirmations'] == [(session.id, body['goal_id'])]
        assert sessions_of(planning_client).find_by_id(session.id) is None

    def test_should_return_the_same_goal_for_the_same_confirmation_key(
        self, planning_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session = _proposed_session((SEED_ADAPTIVE_SKILL_ID,))
        sessions_of(planning_client).add(session)
        first = _confirm(planning_client, session.id)
        assert first.status_code == 200, first.text
        goals_after_first = _goal_count(postgres_database)

        # The planning is gone after success; the same key still recovers the Goal.
        replay = _confirm(planning_client, session.id)

        assert replay.status_code == 200, replay.text
        assert replay.json() == {'goal_id': first.json()['goal_id'], 'replayed': True}
        assert _goal_count(postgres_database) == goals_after_first

    def test_should_refuse_a_repeated_key_with_another_content(
        self, planning_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session = _proposed_session((SEED_ADAPTIVE_SKILL_ID,))
        sessions_of(planning_client).add(session)
        assert _confirm(planning_client, session.id).status_code == 200
        other = _proposed_session((SEED_ADAPTIVE_SKILL_ID,))
        sessions_of(planning_client).add(other)
        goals_before = _goal_count(postgres_database)

        response = _confirm(planning_client, other.id, title='Outro título')

        assert response.status_code == 409, response.text
        assert _goal_count(postgres_database) == goals_before
        assert sessions_of(planning_client).find_by_id(other.id) is not None

    def test_should_keep_the_proposal_when_a_skill_cannot_start_yet(
        self, planning_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session = _proposed_session(
            (SEED_ADAPTIVE_SKILL_ID, SEED_GRAPH_HTML_CSS_SKILL_ID)
        )
        sessions_of(planning_client).add(session)
        goals_before = _goal_count(postgres_database)

        response = _confirm(planning_client, session.id)

        assert response.status_code == 409, response.text
        assert response.json()['code'] == 'conflict'
        assert _goal_count(postgres_database) == goals_before
        stored = sessions_of(planning_client).find_by_id(session.id)
        assert stored is not None
        assert stored.proposal is not None

    def test_should_refuse_a_planning_that_is_not_reviewing_a_proposal(
        self, planning_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        interviewing = interviewing_session()
        processing = started_session()
        sessions_of(planning_client).add(interviewing)
        sessions_of(planning_client).add(processing)
        goals_before = _goal_count(postgres_database)

        assert _confirm(planning_client, interviewing.id).status_code == 409
        assert _confirm(planning_client, processing.id).status_code == 409
        assert _goal_count(postgres_database) == goals_before

    def test_should_report_an_unknown_planning_without_a_stored_confirmation(
        self, planning_client: TestClient
    ) -> None:
        response = _confirm(planning_client, '01ARZ3NDEKTSV4RRFFQ69G5FAV')

        assert response.status_code == 404

    def test_should_reject_an_invalid_body(self, planning_client: TestClient) -> None:
        session = _proposed_session((SEED_ADAPTIVE_SKILL_ID,))
        sessions_of(planning_client).add(session)

        assert _confirm(planning_client, session.id, key='not-a-key').status_code == 422
        assert _confirm(planning_client, session.id, title='   ').status_code == 422
        tampered = planning_client.post(
            f'/intelligence/planning-sessions/{session.id}/confirm',
            json={
                'confirmation_key': CONFIRMATION_KEY,
                'title': TITLE,
                'description': DESCRIPTION,
                'skills': [{'skill_id': SEED_GRAPH_HTML_CSS_SKILL_ID}],
            },
        )
        assert tampered.status_code == 422
        assert sessions_of(planning_client).find_by_id(session.id) is not None
