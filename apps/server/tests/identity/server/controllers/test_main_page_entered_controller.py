"""Registered HTTP mapping for the authenticated main-page event boundary."""

from fastapi.testclient import TestClient
from shifu.app import FastAPIApp
from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.domain.errors import AppError
from tests.fixtures.postgres_fixture import PostgresDatabase


class TestMainPageEnteredController:
    def test_application_error_uses_identity_response(
        self, postgres_database: PostgresDatabase
    ) -> None:
        app = FastAPIApp.register(postgres_database.engine)

        def unavailable_identity() -> None:
            raise AppError

        app.dependency_overrides[IdentityPipe.get_authenticated_user] = (
            unavailable_identity
        )
        with TestClient(app) as client:
            response = client.post('/identity/main-page-entries')
        assert response.status_code == 503
        assert response.json() == {
            'code': 'identity_unavailable',
            'message': 'O serviço de identidade está temporariamente indisponível.',
        }
