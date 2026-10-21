import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from tests.fixtures.postgres_fixture import PostgresDatabase


@pytest.mark.parametrize(
    'schema',
    ('agentos_intelligence', 'agentos_learning'),
)
def test_agentos_runtime_role_can_use_schema_without_creating_objects(
    postgres_runtime: PostgresDatabase,
    schema: str,
) -> None:
    runtime_engine = create_engine(postgres_runtime.agentos_url)
    try:
        with runtime_engine.connect() as connection:
            assert connection.execute(
                text('SELECT has_schema_privilege(current_user, :schema, :privilege)'),
                {'schema': schema, 'privilege': 'USAGE'},
            ).scalar_one()
            assert not connection.execute(
                text('SELECT has_schema_privilege(current_user, :schema, :privilege)'),
                {'schema': schema, 'privilege': 'CREATE'},
            ).scalar_one()

        with pytest.raises(DBAPIError), runtime_engine.begin() as connection:
            connection.execute(
                text(f'CREATE TABLE {schema}.runtime_ddl_forbidden (id integer)')
            )

        session_id = f'role-privilege-test-{schema}'
        with runtime_engine.begin() as connection:
            connection.execute(
                text(
                    f'INSERT INTO {schema}.agentos_sessions '  # noqa: S608 - Schema is chosen from the fixed test parameter set.
                    '(session_id, session_type, created_at) '
                    'VALUES (:session_id, :session_type, :created_at)'
                ),
                {
                    'session_id': session_id,
                    'session_type': 'agent',
                    'created_at': 1,
                },
            )
            connection.execute(
                text(
                    f'UPDATE {schema}.agentos_sessions '  # noqa: S608 - Schema is chosen from the fixed test parameter set.
                    'SET updated_at = :updated_at WHERE session_id = :session_id'
                ),
                {'updated_at': 2, 'session_id': session_id},
            )
            assert (
                connection.execute(
                    text(
                        f'SELECT updated_at FROM {schema}.agentos_sessions '  # noqa: S608 - Schema is chosen from the fixed test parameter set.
                        'WHERE session_id = :session_id'
                    ),
                    {'session_id': session_id},
                ).scalar_one()
                == 2
            )
            connection.execute(
                text(
                    f'DELETE FROM {schema}.agentos_sessions '  # noqa: S608 - Schema is chosen from the fixed test parameter set.
                    'WHERE session_id = :session_id'
                ),
                {'session_id': session_id},
            )
    finally:
        runtime_engine.dispose()


def test_agentos_migration_matches_declared_database_models(
    postgres_runtime: PostgresDatabase,
) -> None:
    completed = _run_alembic(postgres_runtime, 'check')
    assert completed.returncode == 0, 'Alembic model comparison failed.'


def test_agentos_migration_can_be_downgraded_and_reapplied(
    postgres_runtime: PostgresDatabase,
) -> None:
    downgraded = _run_alembic(postgres_runtime, 'downgrade', '341cb645e630')
    assert downgraded.returncode == 0, 'Alembic downgrade failed.'
    try:
        with postgres_runtime.engine.connect() as connection:
            assert connection.execute(
                text("SELECT to_regnamespace('agentos_intelligence') IS NULL")
            ).scalar_one()
            assert connection.execute(
                text("SELECT to_regnamespace('agentos_learning') IS NULL")
            ).scalar_one()
    finally:
        upgraded = _run_alembic(postgres_runtime, 'upgrade', 'head')
        assert upgraded.returncode == 0, 'Alembic re-upgrade failed.'

    with postgres_runtime.engine.connect() as connection:
        assert connection.execute(
            text("SELECT to_regnamespace('agentos_intelligence') IS NOT NULL")
        ).scalar_one()
        assert connection.execute(
            text("SELECT to_regnamespace('agentos_learning') IS NOT NULL")
        ).scalar_one()


def _run_alembic(
    postgres_runtime: PostgresDatabase, *arguments: str
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment['DATABASE_URL'] = postgres_runtime.url
    return subprocess.run(  # noqa: S603 - Command and arguments are controlled by this test.
        [sys.executable, '-m', 'alembic', *arguments],
        cwd=Path(__file__).resolve().parents[4],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
