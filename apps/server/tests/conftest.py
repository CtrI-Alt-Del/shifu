from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import redis
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.shared.settings import get_settings

if TYPE_CHECKING:
    from collections.abc import Generator

    from tests.fixtures.postgres_fixture import PostgresDatabase

pytest_plugins = (
    'tests.fixtures.inngest_fixture',
    'tests.fixtures.postgres_fixture',
    'tests.fixtures.redis_fixture',
)


@pytest.fixture(autouse=True)
def _reset_rate_limit_state() -> Generator[None]:
    """Every REST test shares one client IP against one Redis instance, so the
    token bucket from `RateLimitMiddleware` persists across tests unless it is
    cleared; without this, tests later in the run see 429s that have nothing
    to do with their own behavior."""

    client = redis.Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
        get_settings().redis_url
    )
    try:
        for key in client.scan_iter(  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            match='rate-limit:*'
        ):
            client.delete(key)  # pyright: ignore[reportUnknownArgumentType]
        yield
    finally:
        client.close()


@pytest.fixture
def client(postgres_database: PostgresDatabase) -> Generator[TestClient]:
    with TestClient(FastAPIApp.register(postgres_database.engine)) as test_client:
        yield test_client
