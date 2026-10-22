from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from shifu.shared.rest.middlewares.telemetry_middleware import TelemetryMiddleware
from shifu.shared.rest.pipes.telemetry_pipe import TelemetryPipe

if TYPE_CHECKING:
    from shifu.shared.core.interfaces.telemetry_provider import (
        TelemetryEventInput,
        TelemetryProvider,
    )


class _Provider:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def emit(self, event: TelemetryEventInput) -> None:
        self.events.append(dict(event))


class _FailingProvider:
    def emit(self, event: TelemetryEventInput) -> None:
        del event
        raise RuntimeError('telemetry sink unavailable')


def _build_app(provider: TelemetryProvider) -> FastAPI:
    app = FastAPI()
    app.state.telemetry_provider = provider

    @app.get('/health/{component}')
    def health(component: str) -> dict[str, str]:
        return {'component': component}

    app.add_middleware(TelemetryMiddleware)
    return app


def test_preserves_valid_request_id_and_emits_route_template() -> None:
    provider = _Provider()
    request_id = '123e4567-e89b-42d3-a456-426614174000'

    with TestClient(_build_app(provider)) as client:
        response = client.get(
            '/health/database',
            headers={'X-Request-ID': request_id},
        )

    assert response.status_code == 200
    assert response.headers['X-Request-ID'] == request_id
    event = provider.events[-1]
    assert event['event'] == 'http.request.completed'
    assert event['request_id'] == request_id
    assert event['route'] == '/health/{component}'
    assert event['status_code'] == 200
    assert event['result'] == 'success'
    assert len(provider.events) == 1


def test_replaces_invalid_request_id_with_uuid_v4() -> None:
    provider = _Provider()

    with TestClient(_build_app(provider)) as client:
        response = client.get(
            '/health/database',
            headers={'X-Request-ID': 'password=secret-token'},
        )

    generated_id = response.headers['X-Request-ID']
    assert UUID(generated_id).version == 4
    assert 'password=secret-token' not in str(provider.events)


def test_provider_failure_does_not_change_http_result() -> None:
    with TestClient(_build_app(_FailingProvider())) as client:
        response = client.get('/health/database')

    assert response.status_code == 200
    assert response.json() == {'component': 'database'}
    assert UUID(response.headers['X-Request-ID']).version == 4


def test_pipe_resolves_provider_and_emits_optional_events() -> None:
    provider = _Provider()
    app = FastAPI()
    app.state.telemetry_provider = provider

    @app.get('/pipe')
    def pipe(request: Request) -> dict[str, object]:
        request.state.request_id = 'request-1'
        assert TelemetryPipe.get_telemetry_provider(request) is provider
        assert TelemetryPipe.get_provider(request) is provider
        TelemetryPipe.emit(
            None,
            {'level': 'INFO', 'event': 'app.startup.completed'},
        )
        TelemetryPipe.emit(
            provider,
            {'level': 'INFO', 'event': 'app.startup.completed'},
        )
        return {'request_id': TelemetryPipe.get_request_id(request)}

    with TestClient(app) as client:
        response = client.get('/pipe')

    assert response.status_code == 200
    assert response.json() == {'request_id': 'request-1'}
    assert len(provider.events) == 1


def test_pipe_returns_none_for_missing_provider_and_non_string_request_id() -> None:
    app = FastAPI()

    @app.get('/pipe')
    def pipe(request: Request) -> dict[str, object]:
        request.state.request_id = 123
        assert TelemetryPipe.get_telemetry_provider(request) is None
        assert TelemetryPipe.get_provider(request) is None
        TelemetryPipe.emit(
            None,
            {'level': 'INFO', 'event': 'app.startup.completed'},
        )
        return {'request_id': TelemetryPipe.get_request_id(request)}

    with TestClient(app) as client:
        response = client.get('/pipe')

    assert response.status_code == 200
    assert response.json() == {'request_id': None}
