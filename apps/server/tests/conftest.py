from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault(
    'SHIFU_COMMUNICATION_ENCRYPTION_KEYS',
    'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=',
)

from shifu.app import FastAPIApp
from shifu.shared.constants import ENVIRONMENT

if TYPE_CHECKING:
    from collections.abc import Generator

    from tests.fixtures.postgres_fixture import PostgresDatabase

pytest_plugins = (
    'tests.fixtures.inngest_fixture',
    'tests.fixtures.postgres_fixture',
    'tests.fixtures.redis_fixture',
)


@pytest.fixture
def client(postgres_database: PostgresDatabase) -> Generator[TestClient]:
    with TestClient(
        FastAPIApp.register(postgres_database.engine),
        headers={'x-shifu-bff-secret': ENVIRONMENT.bff_shared_secret},
    ) as test_client:
        yield test_client
