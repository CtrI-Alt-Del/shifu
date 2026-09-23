from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
import os
from pathlib import Path
import subprocess
import sys
from typing import TYPE_CHECKING, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, inspect, insert, select, text
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
        assert body['goalId'] == SEED_GOAL_ID
        assert body['skillId'] == SEED_SKILL_LOGIC_ID
        assert body['isFocus'] is True
        assert 'goal_id' not in body
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
        assert body['items'][1]['latestScore'] == 65
        assert body['recommendation']['activityId'] == body['items'][3]['id']
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

    def test_migration_rejects_easy_score_for_distinct_hard_activity(
        self,
        legacy_postgres_database: PostgresDatabase,
    ) -> None:
        _insert_legacy_mastered_rows(legacy_postgres_database)

        result = _run_alembic(
            legacy_postgres_database.url,
            'upgrade',
            'head',
            check=False,
        )

        assert result.returncode != 0
        assert 'Cannot preserve mastered competency invariants during migration' in (
            result.stdout + result.stderr
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


@pytest.fixture
def legacy_postgres_database(
    postgres_runtime: PostgresDatabase,
) -> Iterator[PostgresDatabase]:
    _clear_application_tables(postgres_runtime.engine)
    _run_alembic(postgres_runtime.url, 'downgrade', 'c4d82f1e7a30')
    try:
        yield postgres_runtime
    finally:
        _clear_application_tables(postgres_runtime.engine)
        _run_alembic(postgres_runtime.url, 'upgrade', 'head')
        _clear_application_tables(postgres_runtime.engine)


def _run_alembic(
    database_url: str,
    command: str,
    target: str,
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment['DATABASE_URL'] = database_url
    return subprocess.run(  # noqa: S603 - command and target are fixed test inputs
        [sys.executable, '-m', 'alembic', command, target],
        cwd=Path(__file__).parents[4],
        env=environment,
        check=check,
        capture_output=True,
        text=True,
    )


def _clear_application_tables(engine: Engine) -> None:
    with engine.begin() as connection:
        table_names = connection.execute(
            text(
                'SELECT tablename FROM pg_tables '
                "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
            )
        ).scalars()
        quoted_table_names = ', '.join(
            f'"{table_name.replace(chr(34), chr(34) * 2)}"'
            for table_name in table_names
        )
        if quoted_table_names:
            connection.execute(
                text(f'TRUNCATE TABLE {quoted_table_names} RESTART IDENTITY CASCADE')
            )


def _insert_legacy_mastered_rows(database: PostgresDatabase) -> None:
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    skill_id = '01SHF000000000000000000100'
    competency_id = '01SHF000000000000000000101'
    easy_activity_id = '01SHF000000000000000000102'
    hard_activity_id = '01SHF000000000000000000103'
    goal_id = '01SHF000000000000000000104'
    experience_id = '01SHF000000000000000000105'
    progress_id = '01SHF000000000000000000106'
    attempt_id = '01SHF000000000000000000107'
    evaluation_id = '01SHF000000000000000000108'

    with database.engine.begin() as connection:
        connection.execute(
            text(
                'INSERT INTO curriculum_skills (id, name, description) '
                'VALUES (:id, :name, :description)'
            ),
            {
                'id': skill_id,
                'name': 'Migration test skill',
                'description': 'Migration test skill.',
            },
        )
        connection.execute(
            text(
                'INSERT INTO curriculum_competencies '
                '(id, skill_id, name, description, position) '
                'VALUES (:id, :skill_id, :name, :description, :position)'
            ),
            {
                'id': competency_id,
                'skill_id': skill_id,
                'name': 'Migration test competency',
                'description': 'Migration test competency.',
                'position': 1,
            },
        )
        for activity_id, difficulty in (
            (easy_activity_id, 'easy'),
            (hard_activity_id, 'hard'),
        ):
            connection.execute(
                text(
                    'INSERT INTO curriculum_activities '
                    '(id, competency_id, activity_type, difficulty, title, '
                    'objective, questions, evaluation_rule) '
                    'VALUES (:id, :competency_id, :activity_type, :difficulty, '
                    ':title, :objective, :questions, :evaluation_rule)'
                ),
                {
                    'id': activity_id,
                    'competency_id': competency_id,
                    'activity_type': 'multiple-choice',
                    'difficulty': difficulty,
                    'title': f'{difficulty.title()} activity',
                    'objective': 'Migration test activity.',
                    'questions': '{}',
                    'evaluation_rule': '{}',
                },
            )
        connection.execute(
            text(
                'INSERT INTO curriculum_sequences (competency_id, items) '
                'VALUES (:competency_id, :items)'
            ),
            {
                'competency_id': competency_id,
                'items': (
                    '[{"position": 1, "activity_id": "'
                    f'{easy_activity_id}'
                    '"}, {"position": 2, "activity_id": "'
                    f'{hard_activity_id}'
                    '"}]'
                ),
            },
        )
        connection.execute(
            text(
                'INSERT INTO learning_goals '
                '(id, account_id, title, description, created_at, updated_at) '
                'VALUES (:id, :account_id, :title, :description, '
                ':created_at, :updated_at)'
            ),
            {
                'id': goal_id,
                'account_id': '01SHF000000000000000000109',
                'title': 'Migration test goal',
                'description': 'Migration test goal.',
                'created_at': created_at,
                'updated_at': created_at,
            },
        )
        connection.execute(
            text(
                'INSERT INTO learning_skill_experiences '
                '(id, goal_id, skill_id, inclusion_reason, status, created_at, '
                'updated_at, started_at, completed_at, completion_summary) '
                'VALUES (:id, :goal_id, :skill_id, :inclusion_reason, :status, '
                ':created_at, :updated_at, :started_at, :completed_at, '
                ':completion_summary)'
            ),
            {
                'id': experience_id,
                'goal_id': goal_id,
                'skill_id': skill_id,
                'inclusion_reason': 'Migration test experience.',
                'status': 'learning',
                'created_at': created_at,
                'updated_at': created_at,
                'started_at': None,
                'completed_at': None,
                'completion_summary': None,
            },
        )
        connection.execute(
            text(
                'INSERT INTO learning_competency_progresses '
                '(id, skill_experience_id, competency_id, content_released, '
                'created_at, updated_at, initial_progress, current_progress, '
                'status, mastered_at) VALUES (:id, :experience_id, '
                ':competency_id, :content_released, :created_at, :updated_at, '
                ':initial_progress, :current_progress, :status, :mastered_at)'
            ),
            {
                'id': progress_id,
                'experience_id': experience_id,
                'competency_id': competency_id,
                'content_released': True,
                'created_at': created_at,
                'updated_at': created_at,
                'initial_progress': Decimal('90'),
                'current_progress': Decimal('90'),
                'status': 'mastered',
                'mastered_at': created_at,
            },
        )
        connection.execute(
            text(
                'INSERT INTO learning_activity_attempts '
                '(id, skill_experience_id, competency_id, activity_id, kind, '
                'answers, submitted_at) VALUES (:id, :experience_id, '
                ':competency_id, :activity_id, :kind, :answers, :submitted_at)'
            ),
            {
                'id': attempt_id,
                'experience_id': experience_id,
                'competency_id': competency_id,
                'activity_id': easy_activity_id,
                'kind': 'learning',
                'answers': '{}',
                'submitted_at': created_at,
            },
        )
        connection.execute(
            text(
                'INSERT INTO learning_activity_evaluations '
                '(id, attempt_id, status, parts, started_at, score, '
                'failure_code, completed_at, effect_applied_at) '
                'VALUES (:id, :attempt_id, :status, :parts, :started_at, '
                ':score, :failure_code, :completed_at, :effect_applied_at)'
            ),
            {
                'id': evaluation_id,
                'attempt_id': attempt_id,
                'status': 'completed',
                'parts': '{}',
                'started_at': created_at,
                'score': Decimal('95'),
                'failure_code': None,
                'completed_at': created_at,
                'effect_applied_at': created_at,
            },
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
