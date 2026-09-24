from collections.abc import Iterator
from typing import TYPE_CHECKING, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.curriculum.providers.curriculum_content_provider import (
    DatabaseCurriculumContentProvider,
)
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.database.seed_data import (
    SEED_ACCOUNT_ID,
    SEED_GOAL_ID,
    SEED_SKILL_LOGIC_ID,
    SEED_SKILL_PYTHON_ID,
    build_development_seed,
)
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture

if TYPE_CHECKING:
    from httpx import Response


class _TestAuthenticationProvider:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        if access_token != 'test-access-token':
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=SEED_ACCOUNT_ID,
            display_name='Pessoa Estudante',
            time_zone='America/Sao_Paulo',
        )


@pytest.fixture
def application(
    postgres_database: PostgresDatabase,
    redis_fixture: RedisFixture,
) -> Iterator[FastAPI]:
    _seed_application(postgres_database)
    application = FastAPIApp.register(postgres_database.engine)
    application.state.authentication_provider = _TestAuthenticationProvider()
    application.state.learning_database = SqlalchemyLearningDatabase(
        postgres_database.engine
    )
    application.state.curriculum_content_provider = DatabaseCurriculumContentProvider(
        SqlalchemyCurriculumDatabase(postgres_database.engine)
    )
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client


class TestGetGoalDetailController:
    def test_should_return_owned_goal_detail_without_writing(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        before = _learning_count(postgres_database)

        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _detail_path(SEED_GOAL_ID),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 200
        assert response.headers['cache-control'] == 'private, no-store'
        body = response.json()
        assert body['goalId'] == SEED_GOAL_ID
        assert body['title'] == 'Aprender a programar'
        assert body['description'] == (
            'Construir uma base prática para resolver problemas com código.'
        )
        assert body['skills'] == [
            {
                'skillExperienceId': '01SHF000000000000000000013',
                'skillId': SEED_SKILL_LOGIC_ID,
                'name': 'Lógica de programação',
                'status': 'learning',
                'progress': pytest.approx(78.33333333333333),
                'inclusionReason': 'Fundamento para todo o restante do percurso.',
            },
            {
                'skillExperienceId': '01SHF000000000000000000014',
                'skillId': SEED_SKILL_PYTHON_ID,
                'name': 'Python essencial',
                'status': 'not-started',
                'progress': None,
                'inclusionReason': 'Aplicar a lógica em uma linguagem prática.',
            },
        ]
        assert body['relations'] == [
            {
                'foundationSkillId': SEED_SKILL_LOGIC_ID,
                'skillId': SEED_SKILL_PYTHON_ID,
            }
        ]
        assert _learning_count(postgres_database) == before

    def test_should_keep_unknown_goal_private(self, client: TestClient) -> None:
        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _detail_path('01SHF000000000000000000099'),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 404
        assert response.json() == {
            'code': 'not_found',
            'message': 'O objetivo de aprendizagem não foi encontrado.',
        }

    def test_should_reject_unauthenticated_goal_detail(
        self, client: TestClient
    ) -> None:
        response = cast(
            'Response',
            client.get(_detail_path(SEED_GOAL_ID)),  # pyright: ignore[reportUnknownMemberType]
        )

        assert response.status_code == 401
        assert response.json()['detail']['code'] == 'unauthorized'

    def test_should_reject_malformed_goal_id(self, client: TestClient) -> None:
        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _detail_path('invalid-goal-id'),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 422


def _detail_path(goal_id: str) -> str:
    return f'/learning/goals/{goal_id}'


def _learning_count(database: PostgresDatabase) -> int:
    with database.engine.connect() as connection:
        return int(
            connection.exec_driver_sql(
                'SELECT COUNT(*) FROM learning_competency_progresses'
            ).scalar_one()
        )


def _seed_application(database: PostgresDatabase) -> None:
    seed = build_development_seed()
    curriculum_database = SqlalchemyCurriculumDatabase(database.engine)
    with curriculum_database.transaction() as repositories:
        repositories.skills.add_many(list(seed.skills))
        repositories.skill_foundations.add_many(list(seed.skill_foundations))
        repositories.competencies.add_many(list(seed.competencies))
        repositories.materials.add_many(list(seed.materials))
        repositories.activities.add_many(list(seed.activities))
        repositories.curriculum_sequences.add_many(list(seed.curriculum_sequences))

    learning_database = SqlalchemyLearningDatabase(database.engine)
    with learning_database.transaction() as repositories:
        repositories.goals.add_many(list(seed.goals))
        repositories.skill_experiences.add_many(list(seed.skill_experiences))
        repositories.competency_progresses.add_many(list(seed.competency_progresses))
        repositories.activity_attempts.add_many(list(seed.activity_attempts))
        repositories.activity_evaluations.add_many(list(seed.activity_evaluations))
