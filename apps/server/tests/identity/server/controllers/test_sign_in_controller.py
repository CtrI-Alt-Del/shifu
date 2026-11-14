from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, cast

import pytest
from fastapi.testclient import TestClient
from shifu.app import FastAPIApp
from shifu.identity.core.domain.errors import InvalidCredentialsError
from shifu.identity.core.use_cases import SignInUseCase
from shifu.identity.pipes import IdentityPipe
from shifu.shared.constants import ENVIRONMENT
from shifu.shared.core.domain.errors import AppError, AuthorizationError
from shifu.shared.rest.pipes.telemetry_pipe import TelemetryPipe
from tests.fixtures.telemetry_boundary_fixture import TelemetryBoundaryFixture

if TYPE_CHECKING:
    from fastapi import Request as FastAPIRequest
    from httpx import Response
    from tests.fixtures.postgres_fixture import PostgresDatabase


class TestSignInController:
    def test_should_emit_invalid_credentials_telemetry_for_invalid_credentials(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def refuse(_self: SignInUseCase, _credentials: object) -> object:
            raise InvalidCredentialsError

        def missing_request_id(_request: FastAPIRequest) -> None:
            pass

        monkeypatch.setattr(SignInUseCase, 'execute', refuse)
        monkeypatch.setattr(TelemetryPipe, 'get_request_id', missing_request_id)

        response = cast(
            'Response',
            client.post(
                '/identity/sign-in',
                json={'email': 'learner@example.com', 'password': 'password'},
            ),
        )

        assert response.status_code == 401

    def test_should_emit_forbidden_telemetry_for_authorization_refusal(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def refuse(_self: SignInUseCase, _credentials: object) -> object:
            raise AuthorizationError

        monkeypatch.setattr(SignInUseCase, 'execute', refuse)

        response = cast(
            'Response',
            client.post(
                '/identity/sign-in',
                json={'email': 'learner@example.com', 'password': 'password'},
            ),
        )

        assert response.status_code == 403

    def test_should_issue_a_server_verifiable_pending_handle_for_pending_credentials(
        self,
        client: TestClient,
    ) -> None:
        registration = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/registrations',
                json={
                    'display_name': 'Barbara Liskov',
                    'email': 'barbara@example.com',
                    'password': 'correct horse battery staple',
                },
            ),
        )

        assert registration.status_code == 202

        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/sign-in',
                json={
                    'email': 'barbara@example.com',
                    'password': 'correct horse battery staple',
                },
            ),
        )

        assert response.status_code == 200
        body = response.json()

        assert body['access'] == 'activation-only'
        assert len(body['pending_handle']) == 43
        assert body['pending_handle'] != registration.json()['pending_handle']

        pending_status = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/pending-confirmations/status',
                json={'pending_handle': body['pending_handle']},
            ),
        )

        assert pending_status.status_code == 200
        assert pending_status.json()['state'] in {'cooldown', 'ready'}

    def test_should_serialize_profile_timestamps_as_iso_strings(
        self,
        client: TestClient,
    ) -> None:
        client.post(  # pyright: ignore[reportUnknownMemberType]
            '/identity/registrations',
            json={
                'display_name': 'Barbara Liskov',
                'email': 'barbara@example.com',
                'password': 'correct horse battery staple',
            },
        )

        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/sign-in',
                json={
                    'email': 'barbara@example.com',
                    'password': 'correct horse battery staple',
                },
            ),
        )

        profile = response.json()['profile']

        assert profile['status'] == 'pending-confirmation'
        assert profile['display_name'] == 'Barbara Liskov'
        assert profile['created_at'].endswith('+00:00')
        assert datetime.fromisoformat(profile['created_at']).utcoffset() == timedelta(0)
        assert 'confirmed_at' not in profile
        assert 'time_zone' not in profile

    @pytest.mark.parametrize('failure_type', [AppError, RuntimeError])
    def test_identity_dependency_failure_uses_safe_identity_response(
        self, postgres_database: PostgresDatabase, failure_type: type[Exception]
    ) -> None:
        provider = TelemetryBoundaryFixture()
        app = FastAPIApp.register(postgres_database.engine, telemetry_provider=provider)

        def unavailable_database() -> None:
            raise failure_type('password=secret-token')

        app.dependency_overrides[IdentityPipe.get_database] = unavailable_database
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                '/identity/sign-in',
                headers={'x-shifu-bff-secret': ENVIRONMENT.bff_shared_secret},
                json={'email': 'learner@example.test', 'password': 'password'},
            )

        assert response.status_code == 503
        assert response.json() == {
            'code': 'identity_unavailable',
            'message': 'O serviço de identidade está temporariamente indisponível.',
        }
        assert 'password=secret-token' not in str(provider.events)

    def test_invalid_credentials_uses_the_public_sign_in_response(
        self, client: TestClient
    ) -> None:
        response = client.post(
            '/identity/sign-in',
            json={'email': 'missing@example.test', 'password': 'wrong-password'},
        )
        assert response.status_code == 401
        assert response.json() == {
            'code': 'invalid_credentials',
            'message': 'O e-mail ou a senha são inválidos.',
        }
