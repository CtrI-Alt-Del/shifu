from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.learning.pipes import LearningPipe
from shifu.learning.core.use_cases import EvaluateChoiceActivityUseCase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider
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


_NOW = datetime(2026, 9, 23, 12, tzinfo=UTC)


class _TestAuthenticationProvider:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        if access_token != 'test-access-token':
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=SEED_ACCOUNT_ID,
            display_name='Pessoa Estudante',
            time_zone='America/Sao_Paulo',
        )


class _FixedClockProvider(ClockProvider):
    def now(self) -> datetime:
        return _NOW


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
    application.dependency_overrides[LearningPipe.get_clock_provider] = lambda: (
        _FixedClockProvider()
    )
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client


class TestGetChoiceAttemptController:
    def test_completed_attempt_includes_question_results_and_safe_disclosure(
        self,
        client: TestClient,
        application: FastAPI,
    ) -> None:
        body = _submission_body()
        answers = cast('list[dict[str, object]]', body['answers'])
        answers[0]['selected_option_keys'] = ['incorrect']
        created = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(),
                json=body,
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )
        assert created.status_code == 201, created.json()
        attempt_id = cast('str', created.json()['attempt_id'])
        database: SqlalchemyLearningDatabase = application.state.learning_database
        with database.transaction() as repositories:
            evaluation = repositories.activity_evaluations.find_by_attempt_id(
                attempt_id
            )
            assert evaluation is not None
            run_id = evaluation.run_id
            assert run_id is not None
        EvaluateChoiceActivityUseCase(database, _FixedClockProvider()).execute(
            attempt_id, run_id
        )

        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _attempt_path(attempt_id),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 200, response.json()
        payload = response.json()
        assert payload['status'] == 'completed'
        questions = cast('list[dict[str, object]]', payload['questions'])
        assert [question['question_key'] for question in questions] == [
            'question-one',
            'question-two',
            'question-three',
        ]
        assert [question['selected_option_keys'] for question in questions] == [
            ['incorrect'],
            ['correct'],
            ['correct'],
        ]
        assert [
            question['disclosed_correct_option_keys'] for question in questions
        ] == [
            [],
            ['correct'],
            ['correct'],
        ]

    def test_stale_pending_attempt_becomes_failed_without_result_disclosure(
        self,
        client: TestClient,
        application: FastAPI,
    ) -> None:
        created = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(),
                json=_submission_body(),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )
        assert created.status_code == 201, created.json()
        attempt_id = cast('str', created.json()['attempt_id'])
        database: SqlalchemyLearningDatabase = application.state.learning_database
        with database.transaction() as repositories:
            evaluation = repositories.activity_evaluations.find_by_attempt_id(
                attempt_id
            )
            assert evaluation is not None
            evaluation.started_at = _NOW - timedelta(minutes=6)
            repositories.activity_evaluations.update(evaluation)

        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _attempt_path(attempt_id),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 200
        assert response.json()['status'] == 'failed'
        assert response.json()['retry_allowed'] is True
        assert response.json()['failure_message']
        assert 'score' not in response.json()
        assert 'questions' not in response.json()

    def test_attempt_for_another_hierarchy_is_private_absence(
        self,
        client: TestClient,
    ) -> None:
        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _attempt_path('01SHF000000000000000000099'),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 404


def _attempts_path() -> str:
    return (
        f'/learning/goals/{SEED_GOAL_ID}/skills/{SEED_SKILL_LOGIC_ID}'
        f'/competencies/{SEED_COMPETENCY_REPETITION_ID}'
        f'/activities/{SEED_ACTIVITY_REPETITION_EASY_ID}/attempts'
    )


def _attempt_path(attempt_id: str) -> str:
    return f'{_attempts_path()}/{attempt_id}'


def _submission_body() -> dict[str, object]:
    return {
        'submission_key': '75e29c3d-8bc2-4e4d-9103-cc747a170012',
        'answers': [
            {
                'question_key': question_key,
                'selected_option_keys': ['correct'],
            }
            for question_key in ('question-one', 'question-two', 'question-three')
        ],
    }
