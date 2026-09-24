"""Disposable Redis fixtures for integration tests."""

from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from redis import Redis
from testcontainers.community.redis import RedisContainer


@dataclass(frozen=True, slots=True)
class RedisFixture:
    """A real Redis instance owned by the test session."""

    client: Redis
    url: str


@pytest.fixture(scope='session')
def redis_runtime() -> Iterator[RedisFixture]:
    """Start one disposable Redis instance for integration tests."""

    container = RedisContainer('redis:7-alpine')
    try:
        container.start()
    except Exception as error:  # noqa: BLE001 - unavailable Docker is a test skip.
        pytest.skip(f'Testcontainers Redis unavailable: {error}')

    host = container.get_container_host_ip()
    port = container.get_exposed_port(6379)
    redis_url = f'redis://{host}:{port}/0'
    client = Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
        redis_url
    )

    try:
        client.ping()  # pyright: ignore[reportUnknownMemberType]
        yield RedisFixture(client=client, url=redis_url)
    finally:
        client.close()
        container.stop()


@pytest.fixture(autouse=True)
def redis_fixture(
    redis_runtime: RedisFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[RedisFixture]:
    """Provide a clean real Redis database and point app settings at it."""

    from shifu.shared.settings import get_settings

    redis_runtime.client.flushdb()  # pyright: ignore[reportUnknownMemberType]
    monkeypatch.setenv('REDIS_URL', redis_runtime.url)
    get_settings.cache_clear()
    try:
        yield redis_runtime
    finally:
        redis_runtime.client.flushdb()  # pyright: ignore[reportUnknownMemberType]
        get_settings.cache_clear()
