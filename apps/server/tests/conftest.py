from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp

if TYPE_CHECKING:
    from collections.abc import Generator

    from tests.fixtures.postgres import PostgresDatabase

pytest_plugins = ('tests.fixtures.inngest_fixture', 'tests.fixtures.postgres')


@pytest.fixture
def client(postgres_database: PostgresDatabase) -> Generator[TestClient]:
    with TestClient(FastAPIApp.register(postgres_database.engine)) as test_client:
        yield test_client
