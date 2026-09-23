from collections.abc import Iterator
from typing import TYPE_CHECKING, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.database.seed_data import (
    SEED_ACCOUNT_ID,
    SEED_ACTIVITY_REPETITION_EASY_ID,
    SEED_COMPETENCY_REPETITION_ID,
    SEED_GOAL_ID,
    SEED_REPETITION_ATTEMPT_ID,
    SEED_SKILL_LOGIC_ID,
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
    curriculum_database = SqlalchemyCurriculumDatabase(postgres_database.engine)
    with curriculum_database.transaction() as repositories:
        repositories.skills.add_many(list(seed.skills))
        repositories.skill_foundations.add_many(list(seed.skill_foundations))
        repositories.competencies.add_many(list(seed.competencies))
        repositories.materials.add_many(list(seed.materials))
        repositories.activities.add_many(list(seed.activities))
        repositories.curriculum_sequences.add_many(list(seed.curriculum_sequences))
    learning_database = SqlalchemyLearningDatabase(postgres_database.engine)
    with learning_database.transaction() as repositories:
        repositories.goals.add_many(list(seed.goals))
        repositories.skill_experiences.add_many(list(seed.skill_experiences))
        repositories.competency_progresses.add_many(list(seed.competency_progresses))
        repositories.activity_attempts.add_many(list(seed.activity_attempts))
        repositories.activity_evaluations.add_many(list(seed.activity_evaluations))

    application = FastAPIApp.register(postgres_database.engine)
    application.state.authentication_provider = _TestAuthenticationProvider()
    application.state.inngest_broker = _NoopBroker()
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client


class TestGetChoiceActivityController:
    def test_returns_ordered_safe_questions_without_grading_data(
        self,
        client: TestClient,
    ) -> None:
        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _activity_path(),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 200, response.json()
        body = response.json()
        assert body['activity_id'] == SEED_ACTIVITY_REPETITION_EASY_ID
        assert body['difficulty'] == 'easy'
        assert [question['key'] for question in body['questions']] == [
            'question-one',
            'question-two',
            'question-three',
        ]
        assert body['can_submit'] is True
        assert body['latest_attempt_id'] == SEED_REPETITION_ATTEMPT_ID
        assert body['unresolved_attempt_id'] is None
        assert set(body['questions'][0]['options'][0]) == {'key', 'text'}
        assert 'is_correct' not in str(body)
        assert 'explanation' not in str(body)

    def test_requires_authentication_and_hides_private_absence(
        self,
        client: TestClient,
    ) -> None:
        unauthenticated = cast(
            'Response',
            client.get(_activity_path()),  # pyright: ignore[reportUnknownMemberType]
        )
        private_absence = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _activity_path(goal_id='01SHF000000000000000000099'),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert unauthenticated.status_code == 401
        assert private_absence.status_code == 404
        assert private_absence.json() == {
            'code': 'not_found',
            'message': 'Recurso não encontrado.',
        }

    def test_returns_latest_and_unresolved_attempt_ids_for_return_navigation(
        self,
        client: TestClient,
    ) -> None:
        submitted = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                f'{_activity_path()}/attempts',
                json={
                    'submission_key': '75e29c3d-8bc2-4e4d-9103-cc747a170012',
                    'answers': [
                        {
                            'question_key': question_key,
                            'selected_option_keys': ['correct'],
                        }
                        for question_key in (
                            'question-one',
                            'question-two',
                            'question-three',
                        )
                    ],
                },
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )
        detail = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _activity_path(),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        attempt_id = cast('str', submitted.json()['attempt_id'])
        assert submitted.status_code == 201
        assert detail.status_code == 200
        assert detail.json()['latest_attempt_id'] == attempt_id
        assert detail.json()['unresolved_attempt_id'] == attempt_id
        assert detail.json()['can_submit'] is False


def _activity_path(*, goal_id: str = SEED_GOAL_ID) -> str:
    return (
        f'/learning/goals/{goal_id}/skills/{SEED_SKILL_LOGIC_ID}'
        f'/competencies/{SEED_COMPETENCY_REPETITION_ID}'
        f'/activities/{SEED_ACTIVITY_REPETITION_EASY_ID}'
    )
