"""Disposable PostgreSQL database fixtures for REST integration tests."""

import os
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from testcontainers.community.postgres import PostgresContainer


@dataclass(frozen=True, slots=True)
class PostgresDatabase:
    """A migrated PostgreSQL engine owned by the test session."""

    engine: Engine
    url: str
    agentos_url: str


@pytest.fixture(scope='session')
def postgres_runtime() -> Iterator[PostgresDatabase]:
    """Start one disposable PostgreSQL instance and apply all migrations."""

    container = PostgresContainer(
        'pgvector/pgvector:0.8.1-pg17',
        username='shifu',
        password='change-me',  # noqa: S106 - Disposable Testcontainers credential.
        dbname='shifu',
        driver='psycopg',
    )
    try:
        container.start()
    except Exception as error:  # noqa: BLE001 - unavailable Docker is a test skip.
        pytest.skip(f'Testcontainers PostgreSQL unavailable: {error}')

    database_url = container.get_connection_url()
    agentos_password = 'agentos-test-password'
    agentos_url = (
        make_url(database_url)
        .set(
            username='shifu_agentos_runtime',
            password=agentos_password,
        )
        .render_as_string(hide_password=False)
    )
    server_directory = Path(__file__).parents[2]
    environment = os.environ.copy()
    environment['DATABASE_URL'] = database_url
    environment['AGENTOS_DATABASE_URL'] = agentos_url
    engine: Engine | None = None
    admin_engine = create_engine(database_url, pool_pre_ping=True)
    previous_agentos_url = os.environ.get('AGENTOS_DATABASE_URL')
    os.environ['AGENTOS_DATABASE_URL'] = agentos_url
    from shifu.shared.settings import get_settings

    get_settings.cache_clear()

    try:
        with admin_engine.begin() as connection:
            connection.exec_driver_sql(
                'CREATE ROLE shifu_agentos_runtime LOGIN '
                "PASSWORD 'agentos-test-password' NOSUPERUSER NOCREATEDB "
                'NOCREATEROLE INHERIT'
            )
            connection.execute(
                text('GRANT CONNECT ON DATABASE shifu TO shifu_agentos_runtime')
            )
        subprocess.run(
            [sys.executable, '-m', 'alembic', 'upgrade', 'head'],
            cwd=server_directory,
            env=environment,
            check=True,
        )
        engine = create_engine(database_url, pool_pre_ping=True)
        database = PostgresDatabase(
            engine=engine,
            url=database_url,
            agentos_url=agentos_url,
        )
        yield database
    finally:
        if engine is not None:
            engine.dispose()
        admin_engine.dispose()
        if previous_agentos_url is None:
            os.environ.pop('AGENTOS_DATABASE_URL', None)
        else:
            os.environ['AGENTOS_DATABASE_URL'] = previous_agentos_url
        get_settings.cache_clear()
        container.stop()


@pytest.fixture
def postgres_database(
    postgres_runtime: PostgresDatabase,
) -> Iterator[PostgresDatabase]:
    """Provide a clean database boundary for each REST test."""

    _clear_application_tables(postgres_runtime.engine)
    try:
        yield postgres_runtime
    finally:
        _clear_application_tables(postgres_runtime.engine)


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
