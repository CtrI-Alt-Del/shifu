from collections.abc import Iterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, insert, select, text
from sqlalchemy.exc import IntegrityError

from shifu.app import FastAPIApp
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.curriculum.providers.curriculum_content_provider import (
    DatabaseCurriculumContentProvider,
)
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.domain.structures import RateLimitDecision
from shifu.shared.database.seed_data import (
    SEED_ACCOUNT_ID,
    SEED_ACTIVITY_REPETITION_EASY_ID,
    SEED_COMPETENCY_FUNCTIONS_ID,
    SEED_COMPETENCY_REPETITION_ID,
    SEED_GOAL_ID,
    SEED_SKILL_LOGIC_ID,
    SEED_SKILL_PYTHON_ID,
    build_development_seed,
)
from shifu.shared.database.sqlalchemy.models import EventModel
from shifu.learning.database.sqlalchemy.models import GoalModel, SkillExperienceModel
from tests.fixtures.postgres_fixture import PostgresDatabase

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


class _AllowAllCacheProvider:
    async def consume_rate_limit_token(
        self,
        key: str,
        capacity: int,
        refill_per_second: float,
    ) -> RateLimitDecision:
        del key, capacity, refill_per_second
        return RateLimitDecision(allowed=True, retry_after_seconds=0)


@pytest.fixture
def application(postgres_database: PostgresDatabase) -> Iterator[FastAPI]:
    columns = inspect(postgres_database.engine).get_columns(
        'learning_competency_progresses'
    )
    if not any(column['name'] == 'hard_activity_score' for column in columns):
        pytest.skip(
            'F5 migration d72c0f4e8a31 is required before the F4 controller boundary.'
        )
    _seed_application(postgres_database)
    application = FastAPIApp.register(postgres_database.engine)
    application.state.authentication_provider = _TestAuthenticationProvider()
    application.state.cache_provider = _AllowAllCacheProvider()
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


class TestGetCompetencyDetailController:
    def test_available_detail_uses_ordered_content_and_does_not_write_events(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        before_events = _event_count(postgres_database)

        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _detail_path(
                    SEED_GOAL_ID,
                    SEED_SKILL_LOGIC_ID,
                    SEED_COMPETENCY_REPETITION_ID,
                ),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 200
        body = response.json()
        assert body['availability'] == 'available'
        assert body['is_focus'] is True
        assert body['progress'] == 55
        assert [item['position'] for item in body['items']] == [1, 2, 3, 4, 5]
        assert [item['kind'] for item in body['items']] == [
            'material',
            'activity',
            'material',
            'activity',
            'activity',
        ]
        assert body['items'][1]['id'] == SEED_ACTIVITY_REPETITION_EASY_ID
        assert body['items'][1]['latest_score'] == 65
        assert body['recommendation']['activity_id'] == body['items'][3]['id']
        assert body['recommendation']['type'] == 'new-activity'
        assert _event_count(postgres_database) == before_events

        second_response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _detail_path(
                    SEED_GOAL_ID,
                    SEED_SKILL_LOGIC_ID,
                    SEED_COMPETENCY_REPETITION_ID,
                ),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )
        assert second_response.status_code == 200
        assert _event_count(postgres_database) == before_events

    def test_available_detail_preserves_rows_and_hard_score_snapshots(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        before = _learning_snapshot(postgres_database)

        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _detail_path(
                    SEED_GOAL_ID,
                    SEED_SKILL_LOGIC_ID,
                    SEED_COMPETENCY_REPETITION_ID,
                ),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 200
        assert _learning_snapshot(postgres_database) == before

    def test_goal_owned_by_another_account_is_private(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        other_goal_id = '01SHF000000000000000000098'
        with postgres_database.engine.begin() as connection:
            connection.execute(
                insert(GoalModel).values(
                    id=other_goal_id,
                    account_id='01SHF000000000000000000099',
                    title='Outro objetivo',
                    description='Objetivo de outra conta.',
                    created_at=datetime(2026, 1, 1, tzinfo=UTC),
                    updated_at=datetime(2026, 1, 1, tzinfo=UTC),
                )
            )
            connection.execute(
                insert(SkillExperienceModel).values(
                    id='01SHF000000000000000000097',
                    goal_id=other_goal_id,
                    skill_id=SEED_SKILL_LOGIC_ID,
                    inclusion_reason='Outro contexto válido.',
                    status='not-started',
                    created_at=datetime(2026, 1, 1, tzinfo=UTC),
                    updated_at=datetime(2026, 1, 1, tzinfo=UTC),
                )
            )

        try:
            response = cast(
                'Response',
                client.get(  # pyright: ignore[reportUnknownMemberType]
                    _detail_path(
                        other_goal_id,
                        SEED_SKILL_LOGIC_ID,
                        SEED_COMPETENCY_REPETITION_ID,
                    ),
                    headers={'Authorization': 'Bearer test-access-token'},
                ),
            )
        finally:
            with postgres_database.engine.begin() as connection:
                connection.execute(
                    text(
                        'DELETE FROM learning_skill_experiences WHERE id = :experience_id'
                    ),
                    {'experience_id': '01SHF000000000000000000097'},
                )
                connection.execute(
                    text('DELETE FROM learning_goals WHERE id = :goal_id'),
                    {'goal_id': other_goal_id},
                )

        assert response.status_code == 404

    def test_skill_experience_uniqueness_rejects_duplicate_goal_skill(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        with (
            pytest.raises(IntegrityError),
            postgres_database.engine.begin() as connection,
        ):
            connection.execute(
                insert(SkillExperienceModel).values(
                    id='01SHF000000000000000000096',
                    goal_id=SEED_GOAL_ID,
                    skill_id=SEED_SKILL_LOGIC_ID,
                    inclusion_reason='Duplicata inválida.',
                    status='not-started',
                    created_at=datetime(2026, 1, 1, tzinfo=UTC),
                    updated_at=datetime(2026, 1, 1, tzinfo=UTC),
                )
            )

    def test_missing_bearer_is_unauthorized(self, client: TestClient) -> None:
        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _detail_path(
                    SEED_GOAL_ID,
                    SEED_SKILL_LOGIC_ID,
                    SEED_COMPETENCY_REPETITION_ID,
                )
            ),
        )

        assert response.status_code == 401
        assert response.json()['detail']['code'] == 'unauthorized'

    def test_invalid_bearer_is_unauthorized(self, client: TestClient) -> None:
        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _detail_path(
                    SEED_GOAL_ID,
                    SEED_SKILL_LOGIC_ID,
                    SEED_COMPETENCY_REPETITION_ID,
                ),
                headers={'Authorization': 'Bearer invalid-token'},
            ),
        )

        assert response.status_code == 401
        assert response.json()['detail']['code'] == 'unauthorized'

    def test_valid_private_absence_is_not_found(self, client: TestClient) -> None:
        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _detail_path(
                    '01SHF000000000000000000099',
                    SEED_SKILL_LOGIC_ID,
                    SEED_COMPETENCY_REPETITION_ID,
                ),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 404
        assert response.json() == {
            'code': 'not_found',
            'message': 'Recurso não encontrado.',
        }

    def test_malformed_path_ids_are_rejected_before_the_use_case(
        self,
        client: TestClient,
    ) -> None:
        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _detail_path(
                    'not-a-valid-id',
                    SEED_SKILL_LOGIC_ID,
                    SEED_COMPETENCY_REPETITION_ID,
                ),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 422

    def test_unavailable_detail_omits_protected_fields(
        self,
        client: TestClient,
    ) -> None:
        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _detail_path(
                    SEED_GOAL_ID,
                    SEED_SKILL_PYTHON_ID,
                    SEED_COMPETENCY_FUNCTIONS_ID,
                ),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 200
        body = response.json()
        assert body['availability'] == 'unavailable'
        assert 'progress' not in body
        assert 'status' not in body
        assert 'items' not in body
        assert 'recommendation' not in body

    def test_unexpected_provider_failures_are_safe_service_errors(
        self,
        application: FastAPI,
    ) -> None:
        application.dependency_overrides[
            LearningPipe.get_curriculum_content_provider
        ] = lambda: _failing_provider()
        test_client = TestClient(application, raise_server_exceptions=False)

        try:
            response = cast(
                'Response',
                test_client.get(  # pyright: ignore[reportUnknownMemberType]
                    _detail_path(
                        SEED_GOAL_ID,
                        SEED_SKILL_LOGIC_ID,
                        SEED_COMPETENCY_REPETITION_ID,
                    ),
                    headers={'Authorization': 'Bearer test-access-token'},
                ),
            )
        finally:
            test_client.close()  # pyright: ignore[reportUnknownMemberType]

        assert response.status_code == 503
        assert response.json() == {
            'code': 'service_unavailable',
            'message': 'Serviço temporariamente indisponível.',
        }


def _detail_path(goal_id: str, skill_id: str, competency_id: str) -> str:
    return f'/learning/goals/{goal_id}/skills/{skill_id}/competencies/{competency_id}'


def _event_count(database: PostgresDatabase) -> int:
    with database.engine.connect() as connection:
        return connection.scalar(select(func.count()).select_from(EventModel)) or 0


def _learning_snapshot(database: PostgresDatabase) -> tuple[object, ...]:
    with database.engine.connect() as connection:
        progress_rows = tuple(
            tuple(row)
            for row in connection.execute(
                text(
                    """
                    SELECT id, skill_experience_id, competency_id,
                           current_progress, hard_activity_score, status, mastered_at,
                           updated_at
                    FROM learning_competency_progresses
                    ORDER BY id
                    """
                )
            ).all()
        )
        table_counts = tuple(
            (
                table,
                connection.scalar(query) or 0,
            )
            for table, query in (
                ('learning_goals', text('SELECT COUNT(*) FROM learning_goals')),
                (
                    'learning_skill_experiences',
                    text('SELECT COUNT(*) FROM learning_skill_experiences'),
                ),
                (
                    'learning_competency_progresses',
                    text('SELECT COUNT(*) FROM learning_competency_progresses'),
                ),
                (
                    'learning_activity_attempts',
                    text('SELECT COUNT(*) FROM learning_activity_attempts'),
                ),
                (
                    'learning_activity_evaluations',
                    text('SELECT COUNT(*) FROM learning_activity_evaluations'),
                ),
                ('events', text('SELECT COUNT(*) FROM events')),
            )
        )
        return (progress_rows, table_counts)


def _failing_provider() -> None:
    raise RuntimeError('provider failure')


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
