from __future__ import annotations

from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient
from shifu.app import FastAPIApp
from shifu.communication.database.sqlalchemy import SqlalchemyCommunicationDatabase
from shifu.identity.core.domain.enums import (
    AccountActionTokenDeliveryStatus,
    ConfirmationDeliveryQueueStatus,
)
from shifu.identity.core.interfaces import (
    ConfirmationDeliveryRequest,
    ConfirmationDeliveryResult,
)
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.identity.pipes import IdentityPipe
from shifu.identity.providers.security import PendingConfirmationHandleProvider
from shifu.shared.constants import ENVIRONMENT

if TYPE_CHECKING:
    from httpx import Response
    from tests.fixtures.postgres_fixture import PostgresDatabase


class _UnavailableConfirmationDeliveryGateway:
    def __init__(self) -> None:
        self.requests: list[ConfirmationDeliveryRequest] = []

    def queue(self, request: ConfirmationDeliveryRequest) -> ConfirmationDeliveryResult:
        self.requests.append(request)
        return ConfirmationDeliveryResult(
            status=ConfirmationDeliveryQueueStatus.DELIVERY_UNAVAILABLE
        )


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
            token_repository = repositories.account_action_tokens
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

    def test_registration_records_delivery_unavailable_and_reports_a_delivery_issue(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        gateway = _UnavailableConfirmationDeliveryGateway()
        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[IdentityPipe.get_confirmation_delivery_gateway] = (
            lambda: gateway
        )

        with TestClient(
            app,
            headers={'x-shifu-bff-secret': ENVIRONMENT.bff_shared_secret},
        ) as client:
            registration = cast(
                'Response',
                client.post(  # pyright: ignore[reportUnknownMemberType]
                    '/identity/registrations',
                    json={
                        'display_name': 'Grace Hopper',
                        'email': 'grace@example.com',
                        'password': 'correct horse battery staple',
                    },
                ),
            )
            pending_handle = registration.json()['pending_handle']
            status = cast(
                'Response',
                client.post(  # pyright: ignore[reportUnknownMemberType]
                    '/identity/pending-confirmations/status',
                    json={'pending_handle': pending_handle},
                ),
            )

        assert registration.status_code == 202
        assert registration.json() == {
            'result': 'pending',
            'pending_handle': pending_handle,
            'is_decoy': False,
        }
        assert len(gateway.requests) == 1
        assert gateway.requests[0].recipient_email == 'grace@example.com'
        assert gateway.requests[0].recipient_name == 'Grace Hopper'
        assert status.json() == {
            'state': 'delivery_issue',
            'retry_after_seconds': None,
        }

        identity_database = SqlalchemyIdentityDatabase(engine=postgres_database.engine)
        with identity_database.transaction() as repositories:
            token = repositories.account_action_tokens.find_by_id(
                gateway.requests[0].identity_action_token_id
            )
            assert token is not None
            assert (
                token.delivery_status
                is AccountActionTokenDeliveryStatus.DELIVERY_UNAVAILABLE
            )

    def test_duplicate_registration_returns_a_decoy_without_queueing_delivery(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        gateway = _UnavailableConfirmationDeliveryGateway()
        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[IdentityPipe.get_confirmation_delivery_gateway] = (
            lambda: gateway
        )
        payload = {
            'display_name': 'Grace Hopper',
            'email': 'grace@example.com',
            'password': 'correct horse battery staple',
        }

        with TestClient(
            app,
            headers={'x-shifu-bff-secret': ENVIRONMENT.bff_shared_secret},
        ) as client:
            client.post('/identity/registrations', json=payload)  # pyright: ignore[reportUnknownMemberType]
            duplicate = cast(
                'Response',
                client.post('/identity/registrations', json=payload),  # pyright: ignore[reportUnknownMemberType]
            )

        assert duplicate.status_code == 202
        assert duplicate.json()['is_decoy'] is True
        assert len(gateway.requests) == 1

    def test_framework_validation_uses_public_identity_input_code(
        self, client: TestClient
    ) -> None:
        response = client.post('/identity/registrations', json={})
        assert response.status_code == 422
        assert response.json() == {
            'code': 'invalid_input',
            'message': 'Os dados enviados são inválidos.',
        }
