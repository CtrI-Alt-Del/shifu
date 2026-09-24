from typing import TYPE_CHECKING, cast
from unittest.mock import create_autospec

from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.fakers.identity.entities import AccountFaker
from shifu.identity.core.interfaces import IdentityDatabase, PasswordHashingProvider
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.identity.pipes import IdentityPipe
from shifu.identity.providers.auth.password_hashing.argon2id_hash_provider import (
    Argon2idHashProvider,
)
from shifu.shared.constants import ENVIRONMENT
from tests.fixtures.postgres_fixture import PostgresDatabase

if TYPE_CHECKING:
    from httpx import Response


class TestSignInController:
    def test_infrastructure_failures_use_the_global_identity_handler(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        database = create_autospec(IdentityDatabase, instance=True)
        password_provider = create_autospec(PasswordHashingProvider, instance=True)
        database.transaction.side_effect = RuntimeError('database unavailable')

        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[IdentityPipe.get_database] = lambda: database
        app.dependency_overrides[IdentityPipe.get_password_hashing_provider] = lambda: (
            password_provider
        )

        with TestClient(app, raise_server_exceptions=False) as client:
            response = cast(
                'Response',
                client.post(  # pyright: ignore[reportUnknownMemberType]
                    '/identity/sign-in',
                    json={'email': 'learner@example.com', 'password': 'secret'},
                    headers={'X-Shifu-Bff-Secret': ENVIRONMENT.bff_shared_secret},
                ),
            )

        assert response.status_code == 503
        assert response.json() == {
            'code': 'identity_unavailable',
            'message': 'O serviço de identidade está temporariamente indisponível.',
        }

    def test_invalid_credentials_are_private_and_uniform(
        self,
        client: TestClient,
    ) -> None:
        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/sign-in',
                json={'email': 'unknown@example.com', 'password': 'secret'},
            ),
        )

        assert response.status_code == 401
        assert response.json() == {
            'code': 'invalid_credentials',
            'message': 'O e-mail ou a senha são inválidos.',
        }

    def test_active_credentials_return_safe_authentication_projection(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        account = AccountFaker.fake(
            email='learner@example.com',
            password_hash=Argon2idHashProvider().hash('secret'),
        )
        database = SqlalchemyIdentityDatabase(engine=postgres_database.engine)
        with database.transaction() as repositories:
            repositories.accounts.add(account)

        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/sign-in',
                json={'email': ' learner@example.com ', 'password': 'secret'},
            ),
        )

        assert response.status_code == 200
        body = response.json()
        assert body['profile']['account_id'] == account.id
        assert body['profile']['email'] == account.email
        assert body['access'] == 'protected'
        assert body['access_version'] == account.access_version
        assert 'password' not in body
        assert 'password_hash' not in body
