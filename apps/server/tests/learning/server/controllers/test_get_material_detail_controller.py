from collections.abc import Iterator
from typing import TYPE_CHECKING, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

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
    SEED_ACTIVITY_REPETITION_MEDIUM_ID,
    SEED_COMPETENCY_FUNCTIONS_ID,
    SEED_COMPETENCY_REPETITION_ID,
    SEED_GOAL_ID,
    SEED_MATERIAL_LOGIC_ID,
    SEED_MATERIAL_PYTHON_ID,
    SEED_MATERIAL_REPETITION_FOR_ID,
    SEED_MATERIAL_REPETITION_INTRO_ID,
    SEED_SKILL_LOGIC_ID,
    SEED_SKILL_PYTHON_ID,
    build_development_seed,
)
from shifu.shared.database.sqlalchemy.models import EventModel
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


class TestGetMaterialDetailController:
    def test_released_material_serializes_official_markdown_without_events(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        before_events = _event_count(postgres_database)

        response = _get(client, material_id=SEED_MATERIAL_REPETITION_INTRO_ID)

        assert response.status_code == 200
        body = response.json()
        assert body['availability'] == 'available'
        assert body['goalId'] == SEED_GOAL_ID
        assert body['skillId'] == SEED_SKILL_LOGIC_ID
        assert body['competencyId'] == SEED_COMPETENCY_REPETITION_ID
        assert body['materialId'] == SEED_MATERIAL_REPETITION_INTRO_ID
        assert body['materialTitle'] == 'Por que repetir instruções?'
        assert body['content'].startswith('Estruturas de repetição automatizam')
        assert '```python' in body['content']
        assert 'material_id' not in body
        assert _event_count(postgres_database) == before_events

    def test_released_material_exposes_the_recommendation_of_its_competency(
        self,
        client: TestClient,
    ) -> None:
        material_response = _get(
            client, material_id=SEED_MATERIAL_REPETITION_INTRO_ID
        ).json()
        competency_response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                f'/learning/goals/{SEED_GOAL_ID}/skills/{SEED_SKILL_LOGIC_ID}'
                f'/competencies/{SEED_COMPETENCY_REPETITION_ID}',
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        ).json()

        assert material_response['recommendation'] is not None
        assert (
            material_response['recommendation'] == competency_response['recommendation']
        )
        assert (
            material_response['recommendation']['activityId']
            == SEED_ACTIVITY_REPETITION_MEDIUM_ID
        )

    def test_second_material_of_the_same_competency_keeps_the_same_context(
        self,
        client: TestClient,
    ) -> None:
        response = _get(client, material_id=SEED_MATERIAL_REPETITION_FOR_ID)

        assert response.status_code == 200
        body = response.json()
        assert body['materialTitle'] == 'Repetição com for'
        assert body['competencyId'] == SEED_COMPETENCY_REPETITION_ID
        assert body['content'].startswith('O laço `for` percorre')

    def test_material_of_another_competency_is_a_private_absence(
        self,
        client: TestClient,
    ) -> None:
        response = _get(client, material_id=SEED_MATERIAL_LOGIC_ID)

        assert response.status_code == 404
        assert response.json() == {
            'code': 'not_found',
            'message': 'Recurso não encontrado.',
        }

    def test_material_of_another_skill_is_a_private_absence(
        self,
        client: TestClient,
    ) -> None:
        response = _get(client, material_id=SEED_MATERIAL_PYTHON_ID)

        assert response.status_code == 404

    def test_unreleased_competency_restricts_the_material_content(
        self,
        client: TestClient,
    ) -> None:
        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _path(
                    SEED_GOAL_ID,
                    SEED_SKILL_PYTHON_ID,
                    SEED_COMPETENCY_FUNCTIONS_ID,
                    SEED_MATERIAL_PYTHON_ID,
                ),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 200
        body = response.json()
        assert body['availability'] == 'unavailable'
        assert 'content' not in body
        assert 'materialTitle' not in body
        assert 'recommendation' not in body

    def test_goal_of_another_account_is_a_private_absence(
        self,
        client: TestClient,
    ) -> None:
        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _path(
                    '01SHF000000000000000000099',
                    SEED_SKILL_LOGIC_ID,
                    SEED_COMPETENCY_REPETITION_ID,
                    SEED_MATERIAL_REPETITION_INTRO_ID,
                ),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 404

    def test_missing_bearer_is_unauthorized(self, client: TestClient) -> None:
        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _path(
                    SEED_GOAL_ID,
                    SEED_SKILL_LOGIC_ID,
                    SEED_COMPETENCY_REPETITION_ID,
                    SEED_MATERIAL_REPETITION_INTRO_ID,
                )
            ),
        )

        assert response.status_code == 401
        assert response.json()['detail']['code'] == 'unauthorized'

    def test_malformed_material_id_is_rejected_before_the_use_case(
        self,
        client: TestClient,
    ) -> None:
        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _path(
                    SEED_GOAL_ID,
                    SEED_SKILL_LOGIC_ID,
                    SEED_COMPETENCY_REPETITION_ID,
                    'not-a-valid-id',
                ),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 422


def _get(client: TestClient, *, material_id: str) -> 'Response':
    return cast(
        'Response',
        client.get(  # pyright: ignore[reportUnknownMemberType]
            _path(
                SEED_GOAL_ID,
                SEED_SKILL_LOGIC_ID,
                SEED_COMPETENCY_REPETITION_ID,
                material_id,
            ),
            headers={'Authorization': 'Bearer test-access-token'},
        ),
    )


def _path(goal_id: str, skill_id: str, competency_id: str, material_id: str) -> str:
    return (
        f'/learning/goals/{goal_id}/skills/{skill_id}'
        f'/competencies/{competency_id}/materials/{material_id}'
    )


def _event_count(database: PostgresDatabase) -> int:
    with database.engine.connect() as connection:
        return connection.scalar(select(func.count()).select_from(EventModel)) or 0


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
