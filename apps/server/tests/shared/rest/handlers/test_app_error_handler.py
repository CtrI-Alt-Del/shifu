"""Registered HTTP error contracts and separately labeled defensive argument cases.

The six direct cases supply unreachable malformed callback arguments or frames.
They prove only handler/provider conformance, never routing or persistence.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from io import StringIO
from types import SimpleNamespace, TracebackType
from typing import TYPE_CHECKING, cast

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException
from shifu.app import FastAPIApp
from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.domain.errors import AppError, AuthorizationError
from shifu.shared.pipes import SharedPipe
from tests.shared.telemetry_support import (
    FailingTelemetry,
    RecordingTelemetry,
    observe_errors,
)

if TYPE_CHECKING:
    from tests.fixtures.postgres_fixture import PostgresDatabase

import shifu.shared.providers.console_telemetry_provider.console_telemetry_provider as telemetry_module
from shifu.identity.core.domain.errors import InvalidCredentialsError
from shifu.rest.handlers import AppErrorHandler
from shifu.shared.providers.console_telemetry_provider import (
    ConsoleTelemetryProvider,
)
from shifu.shared.providers.console_telemetry_provider.console_telemetry_provider import (
    TelemetryLoggingHandler,
)


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
    provider = RecordingTelemetry()
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
    provider = RecordingTelemetry()
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

    provider = RecordingTelemetry()
    app.state.telemetry_provider = provider
    request.state.request_id = 'request-1'
    assert TelemetryPipe.get_telemetry_provider(request) is provider
    assert TelemetryPipe.get_provider(request) is provider
    assert TelemetryPipe.get_request_id(request) == 'request-1'
    TelemetryPipe.emit(provider, {'level': 'INFO', 'event': 'app.startup.completed'})
    assert provider.events == [{'level': 'INFO', 'event': 'app.startup.completed'}]


class TestAppErrorHandler:
    @pytest.mark.parametrize('identity', [True, False])
    @pytest.mark.parametrize('unexpected', [True, False])
    def test_failure_response_depends_on_registered_route(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        identity: bool,
        unexpected: bool,
    ) -> None:
        app = cast('FastAPI', client.app)
        provider = RecordingTelemetry()
        app.state.telemetry_provider = provider

        def fail() -> None:
            if unexpected:
                raise RuntimeError('password=secret-token email=learner@example.test')
            raise AppError

        dependency = (
            IdentityPipe.get_database if identity else SharedPipe.get_authenticated_user
        )
        monkeypatch.setitem(app.dependency_overrides, dependency, fail)
        # The canonical client already entered the real application lifespan.
        # This transport observes safe 5xx responses instead of rethrowing them.
        with observe_errors(client) as observer:
            response = (
                observer.post(
                    '/identity/sign-in',
                    json={'email': 'learner@example.test', 'password': 'secret'},
                    headers=dict(client.headers),
                )
                if identity
                else observer.delete('/learning/goals/private-goal')
            )

        expected_status = 503 if unexpected or identity else 500
        expected_code = (
            'identity_unavailable'
            if identity
            else 'service_unavailable'
            if unexpected
            else 'internal_error'
        )
        assert response.status_code == expected_status
        assert response.json()['code'] == expected_code
        assert 'secret-token' not in response.text
        assert 'learner@example.test' not in str(provider.events)
        assert 'secret-token' not in str(provider.events)
        if unexpected:
            event = next(
                event
                for event in provider.events
                if event['event'] == 'error.unexpected'
            )
            assert event.get('error_code') == 'internal_error'
            assert event.get('exception_type') == 'RuntimeError'
            frames = event.get('stack_trace')
            assert frames
            assert all(
                '/' not in frame['file'] and '\\' not in frame['file']
                for frame in frames
            )

    def test_failing_telemetry_does_not_change_safe_error_response(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        app = cast('FastAPI', client.app)
        app.state.telemetry_provider = FailingTelemetry()

        def fail() -> None:
            raise RuntimeError('private failure')

        monkeypatch.setitem(
            app.dependency_overrides, SharedPipe.get_authenticated_user, fail
        )
        with observe_errors(client) as observer:
            response = observer.delete('/learning/goals/private-goal')

        assert response.status_code == 503
        assert response.json() == {
            'code': 'service_unavailable',
            'message': 'Serviço temporariamente indisponível.',
        }

    @pytest.mark.parametrize('framework_error', [True, False])
    def test_authorization_denial_preserves_correlation_and_safe_policy_detail(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        framework_error: bool,
    ) -> None:
        app = cast('FastAPI', client.app)
        provider = RecordingTelemetry()
        app.state.telemetry_provider = provider

        def deny() -> None:
            if framework_error:
                raise HTTPException(
                    403,
                    detail=cast(
                        'str',
                        {
                            'code': 'policy_denied',
                            'message': 'Bloqueado pela política.',
                        },
                    ),
                    headers={'X-Policy': 'denied'},
                )
            raise AuthorizationError

        monkeypatch.setitem(
            app.dependency_overrides, SharedPipe.get_authenticated_user, deny
        )
        request_id = '123e4567-e89b-42d3-a456-426614174000'
        response = client.delete(
            '/learning/goals/private-goal', headers={'X-Request-ID': request_id}
        )

        assert response.status_code == 403
        if framework_error:
            assert response.headers['X-Policy'] == 'denied'
            assert response.json() == {
                'detail': {
                    'code': 'policy_denied',
                    'message': 'Bloqueado pela política.',
                }
            }
        else:
            assert response.json() == {
                'code': 'forbidden',
                'message': 'Acesso não autorizado.',
            }
        event = next(
            event for event in provider.events if event['event'] == 'auth.access.denied'
        )
        assert event.get('request_id') == request_id
        assert event.get('operation') == 'auth.access'
        assert event.get('result') == 'failure'

    @pytest.mark.parametrize('sign_in', [True, False])
    def test_invalid_credentials_is_localized_only_on_sign_in(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, sign_in: bool
    ) -> None:
        app = cast('FastAPI', client.app)

        def fail() -> None:
            raise InvalidCredentialsError

        monkeypatch.setitem(app.dependency_overrides, IdentityPipe.get_database, fail)
        path = '/identity/sign-in' if sign_in else '/identity/registrations'
        payload = {
            'email': 'learner@example.test',
            'password': 'Password123!',
            'display_name': 'Pessoa',
        }
        response = client.post(path, json=payload)

        assert response.status_code == (401 if sign_in else 500)
        assert response.json() == (
            {
                'code': 'invalid_credentials',
                'message': 'O e-mail ou a senha são inválidos.',
            }
            if sign_in
            else {'code': 'internal_error', 'message': 'Ocorreu um erro inesperado.'}
        )

    def test_registration_validation_uses_public_safe_code(
        self, client: TestClient
    ) -> None:
        response = client.post('/identity/registrations', json={})

        assert response.status_code == 422
        assert response.json() == {
            'code': 'invalid_input',
            'message': 'Os dados enviados são inválidos.',
        }

    def test_unexpected_http_failure_filters_hostile_stack_frames(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        app = cast('FastAPI', client.app)
        stream = StringIO()
        app.state.telemetry_provider = ConsoleTelemetryProvider(
            service='shifu-api', environment='local', version='test', stream=stream
        )

        # A controlled external dependency has a hostile source filename.
        # The real error boundary and console serializer must redact it.
        def fail() -> None:
            raise RuntimeError('password=secret-token')

        fail.__code__ = fail.__code__.replace(co_filename='password=secret.py')
        monkeypatch.setitem(
            app.dependency_overrides, SharedPipe.get_authenticated_user, fail
        )
        with observe_errors(client) as observer:
            response = observer.delete('/learning/goals/private-goal')

        assert response.status_code == 503
        records = [json.loads(line) for line in stream.getvalue().splitlines()]
        event = next(
            record for record in records if record['event'] == 'error.unexpected'
        )
        assert event['exception_type'] == 'RuntimeError'
        assert len(event.get('stack_trace', [])) <= 20
        assert 'password=secret' not in stream.getvalue()
        assert all(
            '/' not in frame['file'] and '\\' not in frame['file']
            for frame in event.get('stack_trace', [])
        )

    def test_framework_logs_during_registered_request_are_safe_and_not_duplicated(
        self, postgres_database: PostgresDatabase, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stream = StringIO()
        provider = ConsoleTelemetryProvider(
            service='shifu-api', environment='local', version='test', stream=stream
        )
        app = FastAPIApp.register(postgres_database.engine, telemetry_provider=provider)

        def private_failure() -> None:
            raise RuntimeError('password=secret-token email=learner@example.test')

        def fail() -> None:
            logging.getLogger('uvicorn.access').info('GET /private token=secret-token')
            logging.getLogger('uvicorn.error').error(
                'token=secret-token body=private-content'
            )
            try:
                private_failure()
            except RuntimeError:
                logging.getLogger('uvicorn.error').exception('private-content')
            raise AuthorizationError

        fail.__code__ = fail.__code__.replace(co_filename='password=secret.py')
        monkeypatch.setitem(
            app.dependency_overrides, SharedPipe.get_authenticated_user, fail
        )
        with TestClient(app) as observer:
            response = observer.delete('/learning/goals/private-goal')

        assert response.status_code == 403
        output = stream.getvalue()
        records = [json.loads(line) for line in output.splitlines()]
        errors = [record for record in records if record['event'] == 'error.unexpected']
        assert [record['exception_type'] for record in errors] == [
            'FrameworkError',
            'RuntimeError',
        ]
        assert (
            len(
                [
                    record
                    for record in records
                    if record['event'] == 'http.request.failed'
                ]
            )
            == 1
        )
        assert all(len(record.get('stack_trace', [])) <= 20 for record in errors)
        assert 'secret-token' not in output
        assert 'private-content' not in output
        assert 'learner@example.test' not in output
        assert 'password=secret' not in output
