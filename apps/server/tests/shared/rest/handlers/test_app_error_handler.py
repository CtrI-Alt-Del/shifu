"""Defensive internal telemetry contracts unreachable through registered HTTP.

HTTP errors, correlation and safe responses are covered by owning controller suites.
These cases deliberately supply malformed internal callback arguments or stack frames.
They prove only the handler/provider contract, never routing or persistence.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from io import StringIO
from types import SimpleNamespace, TracebackType
from typing import TYPE_CHECKING, cast

from fastapi import FastAPI, Request

if TYPE_CHECKING:
    import pytest
    from shifu.shared.core.interfaces.telemetry_provider import TelemetryEventInput

import shifu.shared.providers.console_telemetry_provider.console_telemetry_provider as telemetry_module
from shifu.identity.core.domain.errors import InvalidCredentialsError
from shifu.rest.handlers import AppErrorHandler
from shifu.shared.providers.console_telemetry_provider import (
    ConsoleTelemetryProvider,
)
from shifu.shared.providers.console_telemetry_provider.console_telemetry_provider import (
    TelemetryLoggingHandler,
)


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


def test_invalid_credentials_callback_rejects_non_sign_in_internal_context() -> None:
    # Registered credential failures belong to SignInController's HTTP suite.
    # A registration route cannot normally produce this exception type.
    other_response = asyncio.run(
        AppErrorHandler.handle_invalid_credentials(
            _request(FastAPI(), '/identity/registrations'), InvalidCredentialsError()
        )
    )
    assert other_response.status_code == 500
    assert json.loads(cast('bytes', other_response.body).decode()) == {
        'code': 'internal_error',
        'message': 'Ocorreu um erro inesperado.',
    }


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


def test_pipe_resolves_optional_composition_and_invalid_internal_request_id() -> None:
    from shifu.shared.rest.pipes.telemetry_pipe import TelemetryPipe

    app = FastAPI()
    request = _request(app, '/health')
    assert TelemetryPipe.get_telemetry_provider(request) is None
    assert TelemetryPipe.get_provider(request) is None
    request.state.request_id = 123
    assert TelemetryPipe.get_request_id(request) is None
    TelemetryPipe.emit(None, {'level': 'INFO', 'event': 'app.startup.completed'})

    provider = _Provider()
    app.state.telemetry_provider = provider
    request.state.request_id = 'request-1'
    assert TelemetryPipe.get_telemetry_provider(request) is provider
    assert TelemetryPipe.get_provider(request) is provider
    assert TelemetryPipe.get_request_id(request) == 'request-1'
    TelemetryPipe.emit(provider, {'level': 'INFO', 'event': 'app.startup.completed'})
    assert provider.events == [{'level': 'INFO', 'event': 'app.startup.completed'}]
