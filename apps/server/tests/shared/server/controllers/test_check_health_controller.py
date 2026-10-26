import logging
from typing import TYPE_CHECKING, cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from shifu.app import FastAPIApp
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.providers.cache.redis.redis_cache_provider import RedisCacheProvider
from tests.fixtures.telemetry_boundary_fixture import TelemetryBoundaryFixture

if TYPE_CHECKING:
    from httpx import Response
    from tests.fixtures.postgres_fixture import PostgresDatabase


class TestCheckHealthController:
    def test_check_health(self, client: TestClient) -> None:
        response = cast('Response', client.get('/health'))  # pyright: ignore[reportUnknownMemberType]

        assert response.status_code == 200
        assert response.json() == {'status': 'ok', 'name': 'Shifu API'}

    def test_preserves_valid_request_correlation_and_emits_only_one_http_event(
        self, postgres_database: 'PostgresDatabase'
    ) -> None:
        provider = TelemetryBoundaryFixture()
        request_id = '123e4567-e89b-42d3-a456-426614174000'
        with TestClient(
            FastAPIApp.register(postgres_database.engine, telemetry_provider=provider)
        ) as client:
            provider.events.clear()
            response = client.get('/health', headers={'X-Request-ID': request_id})
            logging.getLogger('uvicorn.access').info(
                'GET /health 200 token=secret-token'
            )

        assert response.status_code == 200
        assert response.headers['X-Request-ID'] == request_id
        events = [
            event for event in provider.events if event['event'].startswith('http.')
        ]
        assert len(events) == 1
        assert events[0]['event'] == 'http.request.completed'
        assert events[0].get('request_id') == request_id
        assert events[0].get('route') == '/health'
        assert events[0].get('status_code') == 200
        assert events[0].get('result') == 'success'
        assert 'secret-token' not in str(provider.events)

    def test_replaces_hostile_request_id_and_ignores_collector_failure(
        self, postgres_database: 'PostgresDatabase'
    ) -> None:
        provider = TelemetryBoundaryFixture()
        with TestClient(
            FastAPIApp.register(postgres_database.engine, telemetry_provider=provider)
        ) as client:
            response = client.get(
                '/health', headers={'X-Request-ID': 'password=secret-token'}
            )
            assert UUID(response.headers['X-Request-ID']).version == 4
            assert 'password=secret-token' not in str(provider.events)
            provider.fail = True
            response = client.get('/health')

        assert response.status_code == 200
        assert response.json() == {'status': 'ok', 'name': 'Shifu API'}
        assert UUID(response.headers['X-Request-ID']).version == 4

    def test_application_lifecycle_reports_version_startup_and_shutdown(
        self, postgres_database: 'PostgresDatabase'
    ) -> None:
        provider = TelemetryBoundaryFixture()
        with TestClient(
            FastAPIApp.register(postgres_database.engine, telemetry_provider=provider)
        ):
            pass

        events = [
            event for event in provider.events if event['event'].startswith('app.')
        ]
        assert [event['event'] for event in events] == [
            'app.version.reported',
            'app.startup.completed',
            'app.shutdown.completed',
        ]
        assert all(
            event.get('operation') in {'app.startup', 'app.shutdown'}
            for event in events
        )
        assert all(event.get('result') == 'success' for event in events)

    def test_framework_logging_omits_raw_messages_and_duplicate_access_events(
        self, postgres_database: 'PostgresDatabase'
    ) -> None:
        provider = TelemetryBoundaryFixture()
        with TestClient(
            FastAPIApp.register(postgres_database.engine, telemetry_provider=provider)
        ):
            provider.events.clear()
            logging.getLogger('uvicorn.access').info(
                'GET /health 200 token=secret-token'
            )
            logging.getLogger('uvicorn.error').error(
                'token=secret-token body=private-content'
            )
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

    def test_dependency_failure_composes_safe_unavailable_event(
        self, postgres_database: 'PostgresDatabase', monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = TelemetryBoundaryFixture()

        async def unavailable(_cache: RedisCacheProvider) -> bool:
            raise ConnectionError('redis://user:password@host')

        monkeypatch.setattr(RedisCacheProvider, 'ping', unavailable)
        with (
            pytest.raises(ServiceUnavailableError),
            TestClient(
                FastAPIApp.register(
                    postgres_database.engine, telemetry_provider=provider
                )
            ),
        ):
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
