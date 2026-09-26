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
    SEED_COMPETENCY_CONDITIONS_ID,
    SEED_COMPETENCY_FUNCTIONS_ID,
    SEED_COMPETENCY_REPETITION_ID,
    SEED_COMPETENCY_VARIABLES_ID,
    SEED_GOAL_ID,
    SEED_SKILL_LOGIC_ID,
    SEED_SKILL_PYTHON_ID,
    build_development_seed,
)
from shifu.shared.database.sqlalchemy.models import EventModel
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture

if TYPE_CHECKING:
    from httpx import Response

ABSENT_ID = '01SHF000000000000000000999'


class _TestAuthenticationProvider:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        if access_token != 'test-access-token':
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=SEED_ACCOUNT_ID,
            display_name='Pessoa Estudante',
            time_zone='America/Sao_Paulo',
        )


class _OtherAccountAuthenticationProvider:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        if access_token != 'test-access-token':
            raise AuthorizationError
        return AuthenticatedUser(
            account_id='01SHF000000000000000000777',
            display_name='Outra Pessoa',
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


class TestGetSkillExperienceDetailController:
    def test_owner_reads_the_experience_without_writing_events(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        before_events = _event_count(postgres_database)

        response = _get(client, skill_id=SEED_SKILL_LOGIC_ID)

        assert response.status_code == 200
        body = response.json()
        assert body['goalId'] == SEED_GOAL_ID
        assert body['skillId'] == SEED_SKILL_LOGIC_ID
        assert body['skillName'] == 'Lógica de programação'
        assert body['skillStatus'] == 'learning'
        assert body['evaluation'] is None
        assert 'skill_name' not in body
        assert _event_count(postgres_database) == before_events

    def test_lists_every_competency_in_curricular_order_with_its_state(
        self,
        client: TestClient,
    ) -> None:
        body = _get(client, skill_id=SEED_SKILL_LOGIC_ID).json()

        competencies = body['competencies']
        assert [item['position'] for item in competencies] == [1, 2, 3]
        assert [item['competencyId'] for item in competencies] == [
            SEED_COMPETENCY_VARIABLES_ID,
            SEED_COMPETENCY_REPETITION_ID,
            SEED_COMPETENCY_CONDITIONS_ID,
        ]
        assert [item['status'] for item in competencies] == [
            'mastered',
            'developing',
            'mastered',
        ]
        assert [item['availability'] for item in competencies] == [
            'available',
            'available',
            'available',
        ]

    def test_focus_is_the_first_competency_that_is_not_mastered(
        self,
        client: TestClient,
    ) -> None:
        body = _get(client, skill_id=SEED_SKILL_LOGIC_ID).json()

        assert body['focusCompetencyId'] == SEED_COMPETENCY_REPETITION_ID
        assert body['focusCompetencyName'] == 'Estruturas de repetição'
        focused = [item for item in body['competencies'] if item['isFocus']]
        assert len(focused) == 1
        assert focused[0]['competencyId'] == SEED_COMPETENCY_REPETITION_ID

    def test_overall_result_averages_every_competency(
        self,
        client: TestClient,
    ) -> None:
        body = _get(client, skill_id=SEED_SKILL_LOGIC_ID).json()

        progresses = [item['progress'] for item in body['competencies']]
        assert progresses == [90.0, 55.0, 90.0]
        assert body['overallResult'] == pytest.approx(sum(progresses) / 3)

    def test_recommendation_matches_the_focus_competency_endpoint(
        self,
        client: TestClient,
    ) -> None:
        skill_body = _get(client, skill_id=SEED_SKILL_LOGIC_ID).json()
        competency_body = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                f'/learning/goals/{SEED_GOAL_ID}/skills/{SEED_SKILL_LOGIC_ID}'
                f'/competencies/{SEED_COMPETENCY_REPETITION_ID}',
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        ).json()

        recommendation = skill_body['recommendation']
        assert recommendation is not None
        assert recommendation['activityId'] == SEED_ACTIVITY_REPETITION_MEDIUM_ID
        assert recommendation['competencyId'] == SEED_COMPETENCY_REPETITION_ID
        assert recommendation['competencyName'] == 'Estruturas de repetição'
        assert recommendation['activityTitle'] == 'Controle a condição de parada'
        for field in ('competencyId', 'activityId', 'difficulty', 'type'):
            assert recommendation[field] == competency_body['recommendation'][field]

    def test_blocked_competency_keeps_its_progress_and_stays_unavailable(
        self,
        client: TestClient,
    ) -> None:
        body = _get(client, skill_id=SEED_SKILL_PYTHON_ID).json()

        assert body['skillStatus'] == 'not-started'
        assert len(body['competencies']) == 1
        blocked = body['competencies'][0]
        assert blocked['competencyId'] == SEED_COMPETENCY_FUNCTIONS_ID
        assert blocked['availability'] == 'unavailable'
        assert blocked['progress'] == 0.0
        assert body['overallResult'] == 0.0
        assert body['recommendation'] is None

    def test_skill_outside_the_goal_is_a_private_absence(
        self,
        client: TestClient,
    ) -> None:
        response = _get(client, skill_id=ABSENT_ID)

        assert response.status_code == 404
        assert response.json() == {
            'code': 'not_found',
            'message': 'Recurso não encontrado.',
        }

    def test_goal_of_another_account_is_a_private_absence(
        self,
        application: FastAPI,
    ) -> None:
        application.state.authentication_provider = (
            _OtherAccountAuthenticationProvider()
        )

        with TestClient(application, raise_server_exceptions=False) as client:
            response = _get(client, skill_id=SEED_SKILL_LOGIC_ID)

        assert response.status_code == 404
        assert response.json() == {
            'code': 'not_found',
            'message': 'Recurso não encontrado.',
        }

    def test_missing_bearer_is_unauthorized(self, client: TestClient) -> None:
        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _path(SEED_GOAL_ID, SEED_SKILL_LOGIC_ID)
            ),
        )

        assert response.status_code == 401


def _get(client: TestClient, *, skill_id: str) -> 'Response':
    return cast(
        'Response',
        client.get(  # pyright: ignore[reportUnknownMemberType]
            _path(SEED_GOAL_ID, skill_id),
            headers={'Authorization': 'Bearer test-access-token'},
        ),
    )


def _path(goal_id: str, skill_id: str) -> str:
    return f'/learning/goals/{goal_id}/skills/{skill_id}'


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
