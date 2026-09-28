from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from shifu.app import FastAPIApp
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.learning.core.domain.enums import ActivityEvaluationStatus
from shifu.learning.core.domain.enums import CompetencyProgressStatus
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.database.seed_data import (
    SEED_ACCOUNT_ID,
    SEED_ADAPTIVE_LAB_CONDITIONS_ACTIVITY_IDS,
    SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
    SEED_ADAPTIVE_LAB_GOAL_ID,
    SEED_ADAPTIVE_LAB_SKILL_ID,
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
    learning_started_at = datetime(2026, 1, 1, tzinfo=UTC)
    for experience in seed.skill_experiences:
        experience.start_diagnosis(learning_started_at)
        experience.start_learning(learning_started_at)
    for progress in seed.competency_progresses:
        progress.content_released = True
        progress.initial_progress = Decimal('55')
        progress.current_progress = Decimal('55')
        progress.status = CompetencyProgressStatus.DEVELOPING
    curriculum_database = SqlalchemyCurriculumDatabase(postgres_database.engine)
    with curriculum_database.transaction() as repositories:
        repositories.skills.add_many(list(seed.skills))
        repositories.skill_foundations.add_many(list(seed.skill_foundations))
        repositories.competencies.add_many(list(seed.competencies))
        repositories.concepts.add_many(list(seed.concepts))
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


class TestRetryChoiceEvaluationController:
    def test_retries_same_attempt_with_new_run_and_one_outbox_event(
        self,
        client: TestClient,
        application: FastAPI,
        postgres_database: PostgresDatabase,
    ) -> None:
        created = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(),
                json=_submission_body(client),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )
        attempt_id = cast('str', created.json()['attempt_id'])
        database: SqlalchemyLearningDatabase = application.state.learning_database
        with database.transaction() as repositories:
            evaluation = repositories.activity_evaluations.find_by_attempt_id(
                attempt_id
            )
            assert evaluation is not None
            evaluation.fail('evaluation_failed')
            repositories.activity_evaluations.update(evaluation)
        before_events = _submission_event_count(postgres_database)

        retried = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _retry_path(attempt_id),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )
        conflict = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _retry_path(attempt_id),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert retried.status_code == 202
        assert retried.json()['attempt_id'] == attempt_id
        assert retried.json()['status'] == 'pending'
        assert retried.json()['retry_allowed'] is False
        assert conflict.status_code == 409
        assert conflict.json()['code'] == 'conflict'
        assert _submission_event_count(postgres_database) == before_events + 1
        with database.transaction() as repositories:
            evaluation = repositories.activity_evaluations.find_by_attempt_id(
                attempt_id
            )
            assert evaluation is not None
            assert evaluation.status is ActivityEvaluationStatus.PENDING
            assert evaluation.run_id is not None

    def test_does_not_reveal_attempt_from_another_goal(
        self,
        client: TestClient,
    ) -> None:
        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _retry_path(
                    '01SHF000000000000000000099',
                    goal_id='01SHF000000000000000000098',
                ),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 404


def _attempts_path() -> str:
    return (
        f'/learning/goals/{SEED_ADAPTIVE_LAB_GOAL_ID}'
        f'/skills/{SEED_ADAPTIVE_LAB_SKILL_ID}'
        f'/competencies/{SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID}'
        f'/activities/{SEED_ADAPTIVE_LAB_CONDITIONS_ACTIVITY_IDS[3]}/attempts'
    )


def _retry_path(
    attempt_id: str,
    *,
    goal_id: str = SEED_ADAPTIVE_LAB_GOAL_ID,
) -> str:
    return (
        f'/learning/goals/{goal_id}/skills/{SEED_ADAPTIVE_LAB_SKILL_ID}'
        f'/competencies/{SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID}'
        f'/activities/{SEED_ADAPTIVE_LAB_CONDITIONS_ACTIVITY_IDS[3]}'
        f'/attempts/{attempt_id}/retry'
    )


def _submission_body(client: TestClient) -> dict[str, object]:
    detail = cast(
        'Response',
        client.get(  # pyright: ignore[reportUnknownMemberType]
            _attempts_path().removesuffix('/attempts'),
            headers={'Authorization': 'Bearer test-access-token'},
        ),
    )
    assert detail.status_code == 200, detail.json()
    questions = cast('list[dict[str, object]]', detail.json()['questions'])
    return {
        'submission_key': '75e29c3d-8bc2-4e4d-9103-cc747a170012',
        'activity_revision': detail.json()['activity_revision'],
        'answers': [
            {
                'kind': 'single_choice',
                'question_key': question['key'],
                'selected_option_keys': [
                    cast(
                        'dict[str, str]', cast('list[object]', question['options'])[0]
                    )['key']
                ],
            }
            for question in questions
        ],
    }


def _submission_event_count(database: PostgresDatabase) -> int:
    with database.engine.connect() as connection:
        return (
            connection.scalar(
                select(func.count())
                .select_from(EventModel)
                .where(EventModel.name == 'learning/activity-submission.requested')
            )
            or 0
        )
