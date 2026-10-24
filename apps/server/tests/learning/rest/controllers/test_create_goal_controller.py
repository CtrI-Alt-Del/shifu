from collections.abc import Iterator
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import func, select

from shifu.app import FastAPIApp
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.learning.core.domain.errors import CurriculumGapError
from shifu.learning.database.sqlalchemy.models import GoalModel
from shifu.learning.rest.learning_error_handler import LearningErrorHandler
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
_UNKNOWN_SKILL_ID = '01SHF999999999999999999999'


def _post(
    client: TestClient,
    payload: dict[str, object],
    headers: dict[str, str] | None = None,
) -> Response:
    return cast(
        'Response',
        client.post('/learning/goals', headers=headers, json=payload),  # pyright: ignore[reportUnknownMemberType]
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
    if CurriculumGapError not in app.exception_handlers:
        LearningErrorHandler.register(app)
    app.state.authentication_provider = _Authentication()
    app.state.inngest_broker = _NoopBroker()
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client


def _count_goals(database: PostgresDatabase) -> int:
    with database.engine.connect() as connection:
        return connection.execute(
            select(func.count()).select_from(GoalModel)
        ).scalar_one()


class TestCreateGoalController:
    def test_creates_a_goal_with_the_selected_skills(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        response = _post(
            client,
            {
                'title': 'Aprender decisões',
                'description': 'Praticar decisões com evidência por Conceito.',
                'skillIds': [SEED_ADAPTIVE_SKILL_ID],
            },
            _AUTHORIZATION,
        )

        assert response.status_code == 201, response.text
        body = response.json()
        assert set(body) == {'goalId', 'skillIds'}
        assert body['skillIds'] == [SEED_ADAPTIVE_SKILL_ID]
        assert _count_goals(postgres_database) == 1

    def test_translates_a_curriculum_gap_into_a_conflict_response(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        response = _post(
            client,
            {
                'title': 'Aprender decisões',
                'description': 'Praticar decisões com evidência por Conceito.',
                'skillIds': [_UNKNOWN_SKILL_ID],
            },
            _AUTHORIZATION,
        )

        assert response.status_code == 409, response.text
        assert response.json() == {
            'code': 'curriculum_gap',
            'message': 'Um Skill selecionado ainda não está pronto para iniciar.',
        }
        assert _count_goals(postgres_database) == 0

    def test_rejects_invalid_bodies_and_requires_authentication(
        self,
        client: TestClient,
    ) -> None:
        missing_description = _post(client, {'title': 'Sem descrição'}, _AUTHORIZATION)
        unauthenticated = _post(
            client, {'title': 'Meta', 'description': 'Descrição', 'skillIds': []}
        )

        assert missing_description.status_code == 422
        assert unauthenticated.status_code == 401
