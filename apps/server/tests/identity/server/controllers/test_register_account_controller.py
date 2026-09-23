from __future__ import annotations

from typing import TYPE_CHECKING, cast

from shifu.communication.database.sqlalchemy import SqlalchemyCommunicationDatabase
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.identity.providers.security import PendingConfirmationHandleProvider

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from httpx import Response
    from shifu.identity.core.interfaces import ConfirmationAccountActionTokensRepository

    from tests.fixtures.postgres_fixture import PostgresDatabase


class TestRegisterAccountController:
    def test_registration_rejects_requests_without_the_bff_secret(
        self,
        client: TestClient,
    ) -> None:
        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/registrations',
                headers={'x-shifu-bff-secret': ''},
                json={
                    'display_name': 'Ada Lovelace',
                    'email': 'ada@example.com',
                    'password': 'correct horse battery staple',
                },
            ),
        )

        assert response.status_code == 401

    def test_invalid_registration_returns_safe_validation_and_creates_nothing(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/registrations',
                json={'display_name': '', 'email': 'invalid', 'password': 'short'},
            ),
        )

        assert response.status_code == 422
        assert response.json()['code'] == 'invalid_input'
        identity_database = SqlalchemyIdentityDatabase(engine=postgres_database.engine)
        with identity_database.transaction() as repositories:
            assert repositories.accounts.find_non_deleted_by_email('invalid') is None

    def test_registration_persists_hashed_token_and_encrypted_communication(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/registrations',
                json={
                    'display_name': 'Ada Lovelace',
                    'email': ' ADA@example.com ',
                    'password': 'correct horse battery staple',
                },
            ),
        )

        assert response.status_code == 202
        body = response.json()
        assert body['result'] == 'pending'
        assert len(body['pending_handle']) == 43

        identity_database = SqlalchemyIdentityDatabase(engine=postgres_database.engine)
        pending_handle_hash = PendingConfirmationHandleProvider().hash(
            body['pending_handle']
        )
        with identity_database.transaction() as repositories:
            account = repositories.accounts.find_non_deleted_by_email('ada@example.com')
            assert account is not None
            token_repository = cast(
                'ConfirmationAccountActionTokensRepository',
                repositories.account_action_tokens,
            )
            token = token_repository.find_by_pending_handle_hash(pending_handle_hash)
            assert token is not None
            assert token.account_id == account.id
            assert token.token_hash != body['pending_handle']
            assert token.communication_id is not None
            communication_id = token.communication_id

        communication_database = SqlalchemyCommunicationDatabase(
            engine=postgres_database.engine
        )
        with communication_database.transaction() as repositories:
            communication = repositories.communications.find_by_id(communication_id)
            assert communication is not None
            assert communication.recipient_email == 'ada@example.com'
            assert communication.content is None
            assert communication.encrypted_content is not None
