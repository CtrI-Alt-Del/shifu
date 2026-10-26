"""Observe request telemetry and application lifecycle at the real health route."""

from typing import TYPE_CHECKING, cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.providers.cache.redis.redis_cache_provider import RedisCacheProvider
from tests.shared.telemetry_support import FailingTelemetry, RecordingTelemetry

if TYPE_CHECKING:
    from fastapi import FastAPI
    from tests.fixtures.postgres_fixture import PostgresDatabase


class TestCheckHealthController:
    def test_preserves_request_id_and_emits_one_safe_http_event(
        self, client: TestClient
    ) -> None:
        app = cast('FastAPI', client.app)
        provider = RecordingTelemetry()
        app.state.telemetry_provider = provider
        request_id = '123e4567-e89b-42d3-a456-426614174000'

        response = client.get('/health', headers={'X-Request-ID': request_id})

        assert response.status_code == 200
        assert response.json() == {'status': 'ok', 'name': 'Shifu API'}
        assert response.headers['X-Request-ID'] == request_id
        assert len(provider.events) == 1
        event = provider.events[0]
        assert event['event'] == 'http.request.completed'
        assert event.get('request_id') == request_id
        assert event.get('route') == '/health'
        assert event.get('status_code') == 200
        assert event.get('result') == 'success'

    def test_replaces_unsafe_request_id_without_logging_it(
        self, client: TestClient
    ) -> None:
        provider = RecordingTelemetry()
        cast('FastAPI', client.app).state.telemetry_provider = provider

        response = client.get(
            '/health', headers={'X-Request-ID': 'password=secret-token'}
        )

        assert response.status_code == 200
        assert UUID(response.headers['X-Request-ID']).version == 4
        assert 'password=secret-token' not in str(provider.events)

    @pytest.mark.parametrize('provider', [FailingTelemetry(), None])
    def test_optional_or_failing_telemetry_preserves_http_result(
        self, client: TestClient, provider: FailingTelemetry | None
    ) -> None:
        cast('FastAPI', client.app).state.telemetry_provider = provider

        response = client.get('/health')

        assert response.status_code == 200
        assert response.json() == {'status': 'ok', 'name': 'Shifu API'}
        assert UUID(response.headers['X-Request-ID']).version == 4

    def test_real_application_emits_startup_request_and_shutdown(
        self, postgres_database: 'PostgresDatabase'
    ) -> None:
        provider = RecordingTelemetry()
        app = FastAPIApp.register(postgres_database.engine, telemetry_provider=provider)

        with TestClient(app) as client:
            assert client.get('/health').status_code == 200

        lifecycle = [
            event for event in provider.events if event['event'].startswith('app.')
        ]
        assert [event['event'] for event in lifecycle] == [
            'app.version.reported',
            'app.startup.completed',
            'app.shutdown.completed',
        ]
        assert all(
            event.get('operation') in {'app.startup', 'app.shutdown'}
            for event in lifecycle
        )
        assert all(event.get('result') == 'success' for event in lifecycle)

    def test_unavailable_dependency_prevents_healthy_startup_without_secret_leak(
        self, postgres_database: 'PostgresDatabase', monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = RecordingTelemetry()
        app = FastAPIApp.register(postgres_database.engine, telemetry_provider=provider)

        async def unavailable(_self: RedisCacheProvider) -> bool:
            raise ConnectionError('redis://user:password@host')

        monkeypatch.setattr(RedisCacheProvider, 'ping', unavailable)
        with pytest.raises(ServiceUnavailableError), TestClient(app):
            pytest.fail('An unhealthy application must never accept requests')

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
