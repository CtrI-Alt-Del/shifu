from collections.abc import Iterator
from uuid import uuid4
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from httpx import Response

from shifu.app import FastAPIApp
from shifu.learning.database.sqlalchemy.models import SkillExperienceModel
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
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


class TestAbandonDiagnosticController:
    def test_abandons_only_the_current_run_and_clears_persisted_key(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        goal_id = _create_goal(client)
        path = f'/learning/goals/{goal_id}/skills/{SEED_ADAPTIVE_SKILL_ID}'
        first_key = uuid4()
        started = _post(
            client, f'{path}/start', _AUTHORIZATION, {'entry_key': str(first_key)}
        )
        assert started.status_code == 200, started.text

        replacement_key = uuid4()
        replacement = _post(
            client,
            f'{path}/start',
            _AUTHORIZATION,
            {'entry_key': str(replacement_key)},
        )
        assert replacement.status_code == 200, replacement.text
        stale = _post(
            client,
            f'{path}/diagnostic/abandon',
            headers={**_AUTHORIZATION, 'X-Diagnostic-Run-Id': str(first_key)},
        )
        assert stale.status_code == 409, stale.text

        abandoned = _post(
            client,
            f'{path}/diagnostic/abandon',
            headers={**_AUTHORIZATION, 'X-Diagnostic-Run-Id': str(replacement_key)},
        )
        assert abandoned.status_code == 204, abandoned.text
        with postgres_database.engine.connect() as connection:
            experience = connection.execute(
                select(
                    SkillExperienceModel.status,
                    SkillExperienceModel.diagnostic_run_id,
                ).where(
                    SkillExperienceModel.goal_id == goal_id,
                    SkillExperienceModel.skill_id == SEED_ADAPTIVE_SKILL_ID,
                )
            ).one()
        assert experience.status == 'not-started'
        assert experience.diagnostic_run_id is None
