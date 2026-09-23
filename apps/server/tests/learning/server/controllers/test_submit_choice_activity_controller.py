from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, cast
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from shifu.app import FastAPIApp
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.learning.database.sqlalchemy.models import ActivityAttemptModel
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.database.seed_data import (
    SEED_ACCOUNT_ID,
    SEED_ACTIVITY_REPETITION_EASY_ID,
    SEED_COMPETENCY_REPETITION_ID,
    SEED_GOAL_ID,
    SEED_SKILL_LOGIC_ID,
    build_development_seed,
)
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture

if TYPE_CHECKING:
    from httpx import Response


_SUBMISSION_KEY = '75e29c3d-8bc2-4e4d-9103-cc747a170012'


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


class TestSubmitChoiceActivityController:
    def test_creates_attempt_and_same_key_replay_returns_the_same_attempt(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        first = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(),
                json=_body(),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )
        attempt_id = cast('str', first.json()['attempt_id'])
        learning_database = SqlalchemyLearningDatabase(postgres_database.engine)
        with learning_database.transaction() as repositories:
            evaluation = repositories.activity_evaluations.find_by_attempt_id(
                attempt_id
            )
            assert evaluation is not None
            evaluation.complete(Decimal('100'), datetime.now(UTC), ())
            repositories.activity_evaluations.update(evaluation)
        replay = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(),
                json=_body(),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )
        changed_answer = _body()
        changed_answers = cast('list[dict[str, object]]', changed_answer['answers'])
        changed_answers[0]['selected_option_keys'] = ['incorrect']
        key_mismatch = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(),
                json=changed_answer,
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert first.status_code == 201, first.json()
        assert first.json()['status'] == 'pending'
        assert first.json()['result_url'].endswith(
            f'/attempts/{first.json()["attempt_id"]}'
        )
        assert replay.status_code == 200
        assert replay.json() == first.json()
        assert key_mismatch.status_code == 409
        assert key_mismatch.json()['code'] == 'conflict'
        with postgres_database.engine.connect() as connection:
            assert (
                connection.scalar(
                    select(func.count())
                    .select_from(ActivityAttemptModel)
                    .where(ActivityAttemptModel.submission_key == _SUBMISSION_KEY)
                )
                == 1
            )

    def test_rejects_semantically_invalid_answers_and_malformed_body(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        invalid_answer = _body()
        invalid_answers = cast('list[dict[str, object]]', invalid_answer['answers'])
        invalid_answers[0]['selected_option_keys'] = ['not-an-option']
        invalid = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(),
                json=invalid_answer,
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )
        malformed = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(),
                json={'submission_key': 'not-a-uuid', 'answers': []},
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert invalid.status_code == 400
        assert invalid.json()['code'] == 'validation_error'
        assert malformed.status_code == 422
        with postgres_database.engine.connect() as connection:
            assert (
                connection.scalar(
                    select(func.count()).select_from(ActivityAttemptModel)
                )
                == 3
            )


def _attempts_path() -> str:
    return (
        f'/learning/goals/{SEED_GOAL_ID}/skills/{SEED_SKILL_LOGIC_ID}'
        f'/competencies/{SEED_COMPETENCY_REPETITION_ID}'
        f'/activities/{SEED_ACTIVITY_REPETITION_EASY_ID}/attempts'
    )


def _body() -> dict[str, object]:
    return {
        'submission_key': str(UUID(_SUBMISSION_KEY)),
        'answers': [
            {
                'question_key': question_key,
                'selected_option_keys': ['correct'],
            }
            for question_key in ('question-one', 'question-two', 'question-three')
        ],
    }
