from __future__ import annotations

import asyncio
import json
import logging
import sys
from io import StringIO
from types import SimpleNamespace, TracebackType
from typing import TYPE_CHECKING, cast

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

if TYPE_CHECKING:
    import pytest

    from shifu.shared.core.interfaces.telemetry_provider import TelemetryEventInput

from shifu.identity.core.domain.errors import InvalidCredentialsError
from shifu.rest.handlers import AppErrorHandler
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.providers.console_telemetry_provider import (
    ConsoleTelemetryProvider,
)
from shifu.shared.providers.console_telemetry_provider.console_telemetry_provider import (
    TelemetryLoggingHandler,
)
import shifu.shared.providers.console_telemetry_provider.console_telemetry_provider as telemetry_module
from shifu.shared.rest.middlewares.telemetry_middleware import TelemetryMiddleware


class _Provider:
    def __init__(self) -> None:
        self.events: list[TelemetryEventInput] = []

    def emit(self, event: TelemetryEventInput) -> None:
        self.events.append(event)


def _request(app: FastAPI, path: str, request_id: str | None = None) -> Request:
    request = Request(
        {
            'type': 'http',
            'asgi': {'version': '3.0', 'spec_version': '2.0'},
            'http_version': '1.1',
            'method': 'GET',
            'scheme': 'http',
            'path': path,
            'raw_path': path.encode(),
            'query_string': b'',
            'headers': [],
            'client': ('testclient', 50000),
            'server': ('testserver', 80),
            'root_path': '',
            'app': app,
        }
    )
    if request_id is not None:
        request.state.request_id = request_id
    return request


def test_unexpected_error_emits_safe_event_without_exception_message() -> None:
    provider = _Provider()
    app = FastAPI()
    app.state.telemetry_provider = provider

    @app.get('/broken')
    def broken() -> None:
        raise RuntimeError('password=secret-token email=learner@example.test')

    AppErrorHandler.register(app)
    app.add_middleware(TelemetryMiddleware)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/broken')

    assert response.status_code == 503
    error_events = [
        event for event in provider.events if event['event'] == 'error.unexpected'
    ]
    assert error_events
    event = error_events[0]
    assert event.get('error_code') == 'internal_error'
    assert event.get('exception_type') == 'RuntimeError'
    assert 'password=secret-token' not in str(provider.events)
    assert 'learner@example.test' not in str(provider.events)
    stack_trace = event.get('stack_trace')
    assert stack_trace is not None
    assert all(
        '/' not in frame['file'] and '\\' not in frame['file'] for frame in stack_trace
    )


def test_app_error_uses_identity_response_only_on_identity_paths() -> None:
    app = FastAPI()
    identity_response = asyncio.run(
        AppErrorHandler.handle_app_error(
            _request(app, '/identity/main-page-entries'), ValueError()
        )
    )
    other_response = asyncio.run(
        AppErrorHandler.handle_app_error(_request(app, '/other'), ValueError())
    )

    assert identity_response.status_code == 503
    assert other_response.status_code == 500


def test_telemetry_provider_filters_unsafe_stack_frame_filenames() -> None:
    stream = StringIO()
    provider = ConsoleTelemetryProvider(
        service='shifu-api',
        environment='local',
        version='test',
        stream=stream,
    )

    provider.emit(
        {
            'level': 'ERROR',
            'event': 'error.unexpected',
            'stack_trace': [
                {'file': r'C:\workspace\safe-file_1.py', 'line': 10},
                {'file': 'password=secret.py', 'line': 11},
                {'file': 'safe.py<script>', 'line': 12},
            ],
        }
    )

    record = json.loads(stream.getvalue())
    assert record['stack_trace'] == [{'file': 'safe-file_1.py', 'line': 10}]


def test_provider_failure_does_not_change_unexpected_error_response() -> None:
    class _FailingProvider:
        def emit(self, event: TelemetryEventInput) -> None:
            del event
            raise RuntimeError('telemetry sink unavailable')

    provider = _FailingProvider()
    app = FastAPI()
    app.state.telemetry_provider = provider

    @app.get('/broken')
    def broken() -> None:
        raise RuntimeError('private failure')

    AppErrorHandler.register(app)
    app.add_middleware(TelemetryMiddleware)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/broken')

    assert response.status_code == 503
    assert response.json() == {
        'code': 'service_unavailable',
        'message': 'Serviço temporariamente indisponível.',
    }


def test_authorization_error_emits_request_id() -> None:
    provider = _Provider()
    app = FastAPI()
    app.state.telemetry_provider = provider

    response = asyncio.run(
        AppErrorHandler.handle_authorization_error(
            _request(app, '/protected', '123e4567-e89b-42d3-a456-426614174000'),
            AuthorizationError(),
        )
    )

    assert response.status_code == 403
    assert provider.events == [
        {
            'level': 'WARNING',
            'event': 'auth.access.denied',
            'operation': 'auth.access',
            'result': 'failure',
            'error_code': 'forbidden',
            'request_id': '123e4567-e89b-42d3-a456-426614174000',
        }
    ]


def test_unexpected_error_uses_identity_unavailable_response() -> None:
    provider = _Provider()
    app = FastAPI()
    app.state.telemetry_provider = provider

    response = asyncio.run(
        AppErrorHandler.handle_unexpected_error(
            _request(app, '/identity/sign-in'), RuntimeError('private failure')
        )
    )

    assert response.status_code == 503
    assert json.loads(cast('bytes', response.body).decode()) == {
        'code': 'identity_unavailable',
        'message': 'O serviço de identidade está temporariamente indisponível.',
    }


def test_invalid_credentials_uses_sign_in_response_only_on_sign_in_path() -> None:
    app = FastAPI()
    sign_in_response = asyncio.run(
        AppErrorHandler.handle_invalid_credentials(
            _request(app, '/identity/sign-in'), InvalidCredentialsError()
        )
    )
    other_response = asyncio.run(
        AppErrorHandler.handle_invalid_credentials(
            _request(app, '/identity/registrations'), InvalidCredentialsError()
        )
    )

    assert sign_in_response.status_code == 401
    assert json.loads(cast('bytes', sign_in_response.body).decode()) == {
        'code': 'invalid_credentials',
        'message': 'O e-mail ou a senha são inválidos.',
    }
    assert other_response.status_code == 500
    assert json.loads(cast('bytes', other_response.body).decode()) == {
        'code': 'internal_error',
        'message': 'Ocorreu um erro inesperado.',
    }


def test_request_validation_error_uses_public_identity_code() -> None:
    response = asyncio.run(
        AppErrorHandler.handle_request_validation_error(
            _request(FastAPI(), '/identity/registrations'), ValueError()
        )
    )

    assert response.status_code == 422
    assert json.loads(cast('bytes', response.body).decode()) == {
        'code': 'invalid_input',
        'message': 'Os dados enviados são inválidos.',
    }


def test_http_forbidden_error_emits_event_and_preserves_safe_detail() -> None:
    provider = _Provider()
    app = FastAPI()
    app.state.telemetry_provider = provider

    response = asyncio.run(
        AppErrorHandler.handle_http_error(
            _request(app, '/protected', '123e4567-e89b-42d3-a456-426614174000'),
            StarletteHTTPException(
                status_code=403,
                detail=cast(
                    'str', {'code': 'policy_denied', 'message': 'Blocked by policy'}
                ),
                headers={'X-Policy': 'denied'},
            ),
        )
    )

    assert response.status_code == 403
    assert response.headers['X-Policy'] == 'denied'
    assert json.loads(cast('bytes', response.body).decode()) == {
        'detail': {'code': 'policy_denied', 'message': 'Blocked by policy'}
    }
    assert provider.events[0]['event'] == 'auth.access.denied'
    assert (
        provider.events[0].get('request_id') == '123e4567-e89b-42d3-a456-426614174000'
    )


def test_http_handler_emits_safe_event_for_non_http_exception() -> None:
    provider = _Provider()
    app = FastAPI()
    app.state.telemetry_provider = provider

    response = asyncio.run(
        AppErrorHandler.handle_http_error(
            _request(app, '/broken'), RuntimeError('password=secret-token')
        )
    )

    assert response.status_code == 500
    assert json.loads(cast('bytes', response.body).decode()) == {
        'code': 'internal_error',
        'message': 'Ocorreu um erro inesperado.',
    }
    assert provider.events[0]['event'] == 'error.unexpected'
    assert 'password=secret-token' not in str(provider.events)


def test_stack_trace_omits_empty_and_unsafe_frame_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frames = [
        SimpleNamespace(filename='', lineno=0, name=''),
        SimpleNamespace(filename='safe.py', lineno='unknown', name=''),
    ]

    def extract_tb(_traceback: TracebackType | None) -> list[SimpleNamespace]:
        return frames

    monkeypatch.setattr(
        telemetry_module.traceback,
        'extract_tb',
        extract_tb,
    )

    response = asyncio.run(
        AppErrorHandler.handle_unexpected_error(
            _request(FastAPI(), '/broken'), RuntimeError('private failure')
        )
    )

    assert response.status_code == 503


def test_logging_handler_bounds_and_sanitizes_exception_frames(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _Provider()
    handler = TelemetryLoggingHandler(provider)
    hostile_frame = SimpleNamespace(
        filename=r'C:\private\password=secret.py',
        lineno=7,
        name='leak_password=secret',
    )
    safe_frame = SimpleNamespace(
        filename=r'C:\service\safe-handler.py',
        lineno=42,
        name='safe_handler',
    )

    def extract_tb(_traceback: TracebackType | None) -> list[SimpleNamespace]:
        return [safe_frame] * 5 + [hostile_frame] * 19 + [safe_frame]

    monkeypatch.setattr(telemetry_module.traceback, 'extract_tb', extract_tb)

    def _raise_hostile_error() -> None:
        raise RuntimeError('password=secret-token email=learner@example.test')

    record: logging.LogRecord | None = None
    try:
        _raise_hostile_error()
    except RuntimeError:
        record = logging.LogRecord(
            name='uvicorn.error',
            level=logging.ERROR,
            pathname='ignored.py',
            lineno=1,
            msg='raw message must not be inspected',
            args=(),
            exc_info=None,
        )
        record.exc_info = sys.exc_info()

    assert record is not None
    handler.emit(record)

    event = provider.events[0]
    assert event.get('stack_trace') == [
        {'file': 'safe-handler.py', 'line': 42, 'function': 'safe_handler'}
    ]
    assert 'password=secret' not in str(event)
    assert 'learner@example.test' not in str(event)
