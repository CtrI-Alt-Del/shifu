"""Safe shared error contracts through routes registered by FastAPIApp."""

from io import StringIO
import json
import logging
from typing import TYPE_CHECKING, cast

import pytest
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException

from shifu.app import FastAPIApp
from shifu.identity.core.domain.errors import InvalidCredentialsError
from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.domain.errors import AppError, AuthorizationError
from shifu.shared.pipes import SharedPipe
from shifu.shared.providers.console_telemetry_provider import ConsoleTelemetryProvider
from tests.shared.telemetry_support import (
    FailingTelemetry,
    RecordingTelemetry,
    observe_errors,
)


if TYPE_CHECKING:
    from fastapi import FastAPI
    from tests.fixtures.postgres_fixture import PostgresDatabase


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
        self, postgres_database: 'PostgresDatabase', monkeypatch: pytest.MonkeyPatch
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
