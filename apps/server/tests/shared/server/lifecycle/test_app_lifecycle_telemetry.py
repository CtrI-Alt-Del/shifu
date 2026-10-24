from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import os
from typing import TYPE_CHECKING, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

os.environ.setdefault('REDIS_URL', 'redis://127.0.0.1:6379/0')
os.environ.setdefault(
    'SHIFU_COMMUNICATION_ENCRYPTION_KEYS',
    'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=',
)

from shifu.app import FastAPIApp
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.providers.cache.redis.redis_cache_provider import RedisCacheProvider
from shifu.shared.providers.console_telemetry_provider import (
    configure_telemetry_logging,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from shifu.shared.core.interfaces.telemetry_provider import TelemetryEventInput


class _Provider:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def emit(self, event: TelemetryEventInput) -> None:
        self.events.append(dict(event))


class _Cache:
    def __init__(self, *, ping_error: Exception | None = None) -> None:
        self._ping_error = ping_error

    async def ping(self) -> bool:
        if self._ping_error is not None:
            raise self._ping_error
        return True

    async def close(self) -> None:
        return


def test_framework_logging_is_adapted_without_raw_message() -> None:
    provider = _Provider()
    configure_telemetry_logging(provider, log_level='INFO')

    logging.getLogger('uvicorn.access').info('GET /health 200 token=secret-token')
    logging.getLogger('uvicorn.error').error('token=secret-token body=private-content')

    assert provider.events == [
        {
            'level': 'ERROR',
            'event': 'error.unexpected',
            'operation': 'http.request',
            'result': 'failure',
            'error_code': 'internal_error',
            'exception_type': 'FrameworkError',
        }
    ]
    assert 'secret-token' not in str(provider.events)
    assert 'private-content' not in str(provider.events)


def test_access_logging_is_not_a_second_http_event() -> None:
    provider = _Provider()
    configure_telemetry_logging(provider, log_level='INFO')

    logging.getLogger('uvicorn.access').info('GET /health 200')

    assert provider.events == []


def test_application_lifecycle_composes_version_startup_and_shutdown_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _Provider()
    app = FastAPIApp.register(
        create_engine('sqlite:///:memory:'),
        telemetry_provider=provider,
    )
    cache = _Cache()

    @asynccontextmanager
    async def no_op_registry_lifespan() -> AsyncGenerator[None]:
        yield

    def connect(_url: str) -> RedisCacheProvider:
        return cast('RedisCacheProvider', cache)

    monkeypatch.setattr(
        RedisCacheProvider,
        'connect',
        staticmethod(connect),
    )
    monkeypatch.setattr(
        app.state.intelligence_workflows_registry,
        'lifespan',
        lambda: no_op_registry_lifespan(),
    )
    monkeypatch.setattr(
        app.state.learning_workflows_registry,
        'lifespan',
        lambda: no_op_registry_lifespan(),
    )
    monkeypatch.setattr(app.state.inngest_broker, 'start', lambda: None)
    monkeypatch.setattr(app.state.inngest_broker, 'stop', lambda: None)

    with TestClient(app):
        pass

    assert [event['event'] for event in provider.events] == [
        'app.version.reported',
        'app.startup.completed',
        'app.shutdown.completed',
    ]
    assert all(
        event['operation'] in {'app.startup', 'app.shutdown'}
        for event in provider.events
    )
    assert all(event['result'] == 'success' for event in provider.events)


def test_dependency_failure_composes_safe_unavailable_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _Provider()
    app = FastAPIApp.register(
        create_engine('sqlite:///:memory:'),
        telemetry_provider=provider,
    )
    cache = _Cache(ping_error=ConnectionError('redis://user:password@host'))

    def connect(_url: str) -> RedisCacheProvider:
        return cast('RedisCacheProvider', cache)

    monkeypatch.setattr(
        RedisCacheProvider,
        'connect',
        staticmethod(connect),
    )
    monkeypatch.setattr(
        app.state.intelligence_workflows_registry,
        'close',
        lambda: _close_registry(),
    )
    monkeypatch.setattr(
        app.state.learning_workflows_registry,
        'close',
        lambda: _close_registry(),
    )

    with pytest.raises(ServiceUnavailableError), TestClient(app):
        pass

    assert provider.events == [
        {
            'level': 'ERROR',
            'event': 'dependency.unavailable',
            'operation': 'dependency.check',
            'result': 'unavailable',
            'error_code': 'service_unavailable',
        }
    ]
    assert 'redis://user:password@host' not in str(provider.events)


async def _close_registry() -> None:
    return
