from collections.abc import Iterator
from datetime import datetime
from typing import cast
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select

from shifu.app import FastAPIApp
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.learning.database.sqlalchemy.models import SkillExperienceModel
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.database.seed_data import (
    SEED_ACCOUNT_ID,
    SEED_ADAPTIVE_SKILL_ID,
    build_development_seed,
)
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture

_AUTHORIZATION = {'Authorization': 'Bearer test-access-token'}


def _post(
    client: TestClient,
    path: str,
    headers: dict[str, str] | None = None,
    payload: dict[str, object] | None = None,
) -> Response:
    return cast(
        'Response',
        client.post(path, headers=headers, json=payload),  # pyright: ignore[reportUnknownMemberType]
    )


class _Authentication:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        if access_token != 'test-access-token':
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=SEED_ACCOUNT_ID,
            display_name='Pessoa Estudante',
            time_zone='America/Sao_Paulo',
        )


class _NoopBroker:
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


@pytest.fixture
def application(
    postgres_database: PostgresDatabase,
    redis_fixture: RedisFixture,
) -> Iterator[FastAPI]:
    seed = build_development_seed()
    curriculum = SqlalchemyCurriculumDatabase(postgres_database.engine)
    with curriculum.transaction() as repositories:
        repositories.skills.add_many(list(seed.skills))
        repositories.skill_foundations.add_many(list(seed.skill_foundations))
        repositories.competencies.add_many(list(seed.competencies))
        repositories.concepts.add_many(list(seed.concepts))
        repositories.materials.add_many(list(seed.materials))
        repositories.activities.add_many(list(seed.activities))
        repositories.curriculum_sequences.add_many(list(seed.curriculum_sequences))
    app = FastAPIApp.register(postgres_database.engine)
    app.state.authentication_provider = _Authentication()
    app.state.inngest_broker = _NoopBroker()
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client


class TestStartSkillController:
    def test_start_returns_the_run_key_and_replay_is_idempotent(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        goal_id = _create_goal(client)
        path = f'/learning/goals/{goal_id}/skills/{SEED_ADAPTIVE_SKILL_ID}/start'
        entry_key = uuid4()

        started = _post(client, path, _AUTHORIZATION, {'entry_key': str(entry_key)})

        assert started.status_code == 200, started.text
        assert started.json() == {
            'status': 'diagnosing',
            'diagnosticRunId': str(entry_key),
        }
        status, diagnostic_run_id, started_at = _experience(postgres_database, goal_id)

        assert status == 'diagnosing'
        assert diagnostic_run_id == str(entry_key)

        replay = _post(client, path, _AUTHORIZATION, {'entry_key': str(entry_key)})

        assert replay.status_code == 200, replay.text
        assert replay.json() == started.json()
        assert _experience(postgres_database, goal_id)[2] == started_at

        replacement_key = uuid4()
        replacement = _post(
            client, path, _AUTHORIZATION, {'entry_key': str(replacement_key)}
        )

        assert replacement.status_code == 200, replacement.text
        assert replacement.json()['diagnosticRunId'] == str(replacement_key)
        assert _experience(postgres_database, goal_id)[1] == str(replacement_key)

    def test_rejects_missing_or_invalid_entry_key_and_requires_authentication(
        self,
        client: TestClient,
    ) -> None:
        goal_id = _create_goal(client)
        path = f'/learning/goals/{goal_id}/skills/{SEED_ADAPTIVE_SKILL_ID}/start'

        missing_key = _post(client, path, _AUTHORIZATION, {})
        invalid_key = _post(client, path, _AUTHORIZATION, {'entry_key': 'not-a-uuid'})
        unauthenticated = _post(client, path, payload={'entry_key': str(uuid4())})

        assert missing_key.status_code == 422
        assert invalid_key.status_code == 422
        assert unauthenticated.status_code == 401


def _create_goal(client: TestClient) -> str:
    response = _post(
        client,
        '/learning/goals',
        _AUTHORIZATION,
        {
            'title': 'Aprender decisões',
            'description': 'Praticar decisões com evidência por Conceito.',
            'skillIds': [SEED_ADAPTIVE_SKILL_ID],
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()['goalId'])


def _experience(
    database: PostgresDatabase, goal_id: str
) -> tuple[str, str | None, datetime | None]:
    with database.engine.connect() as connection:
        experience = connection.execute(
            select(
                SkillExperienceModel.status,
                SkillExperienceModel.diagnostic_run_id,
                SkillExperienceModel.started_at,
            ).where(
                SkillExperienceModel.goal_id == goal_id,
                SkillExperienceModel.skill_id == SEED_ADAPTIVE_SKILL_ID,
            )
        ).one()
    return cast('tuple[str, str | None, datetime | None]', tuple(experience))
