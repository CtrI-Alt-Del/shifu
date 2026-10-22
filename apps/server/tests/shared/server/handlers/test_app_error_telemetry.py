from __future__ import annotations

import json
import logging
import sys
from io import StringIO
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    import pytest

from shifu.rest.handlers import AppErrorHandler
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
        self.events: list[dict[str, Any]] = []

    def emit(self, event: dict[str, Any]) -> None:
        self.events.append(event)


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
    assert event['error_code'] == 'internal_error'
    assert event['exception_type'] == 'RuntimeError'
    assert 'password=secret-token' not in str(provider.events)
    assert 'learner@example.test' not in str(provider.events)
    assert all(
        '/' not in frame['file'] and '\\' not in frame['file']
        for frame in event['stack_trace']
    )


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
        def emit(self, event: dict[str, Any]) -> None:
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
    monkeypatch.setattr(
        telemetry_module.traceback,
        'extract_tb',
        lambda _traceback: [safe_frame] * 5 + [hostile_frame] * 19 + [safe_frame],
    )

    def _raise_hostile_error() -> None:
        raise RuntimeError('password=secret-token email=learner@example.test')

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

    handler.emit(record)

    event = provider.events[0]
    assert event['stack_trace'] == [
        {'file': 'safe-handler.py', 'line': 42, 'function': 'safe_handler'}
    ]
    assert 'password=secret' not in str(event)
    assert 'learner@example.test' not in str(event)
