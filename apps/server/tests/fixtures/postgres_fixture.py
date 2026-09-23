"""Disposable PostgreSQL database fixtures for REST integration tests."""

from collections.abc import Iterator
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys

import pytest
from sqlalchemy import Engine, create_engine, text
from testcontainers.community.postgres import PostgresContainer


@dataclass(frozen=True, slots=True)
class PostgresDatabase:
    """A migrated PostgreSQL engine owned by the test session."""

    engine: Engine
    url: str


@pytest.fixture(scope='session')
def postgres_runtime() -> Iterator[PostgresDatabase]:
    """Start one disposable PostgreSQL instance and apply all migrations."""

    container = PostgresContainer(
        'postgres:17-alpine',
        username='shifu',
        password='change-me',  # noqa: S106 - disposable test credential
        dbname='shifu',
        driver='psycopg',
    )
    try:
        container.start()
    except Exception as error:  # noqa: BLE001 - unavailable Docker is a test skip.
        pytest.skip(f'Testcontainers PostgreSQL unavailable: {error}')

    database_url = container.get_connection_url()
    server_directory = Path(__file__).parents[2]
    environment = os.environ.copy()
    environment['DATABASE_URL'] = database_url
    engine: Engine | None = None

    try:
        subprocess.run(
            [sys.executable, '-m', 'alembic', 'upgrade', 'head'],
            cwd=server_directory,
            env=environment,
            check=True,
        )
        engine = create_engine(database_url, pool_pre_ping=True)
        database = PostgresDatabase(engine=engine, url=database_url)
        yield database
    finally:
        if engine is not None:
            engine.dispose()
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
