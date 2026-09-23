from __future__ import annotations

from hashlib import sha256
from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
    AccountStatus,
)
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.identity.pipes import IdentityPipe
from shifu.shared.constants import ENVIRONMENT

if TYPE_CHECKING:
    from httpx import Response

    from shifu.identity.core.interfaces import ConfirmationAccountActionTokensRepository
    from tests.fixtures.postgres import PostgresDatabase


class _SequenceActionTokenProvider:
    def __init__(self, *tokens: str) -> None:
        self._tokens = list(tokens)

    def generate(self) -> str:
        return self._tokens.pop(0)

    @staticmethod
    def hash(token: str) -> str:
        return sha256(token.encode('utf-8')).hexdigest()


class _FixedPendingHandleProvider:
    def generate(self) -> str:
        return 'B' * 43

    @staticmethod
    def hash(token: str) -> str:
        return sha256(token.encode('utf-8')).hexdigest()


class TestConfirmAccountController:
    def test_valid_token_activates_account_and_returns_safe_profile(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        action_token = 'A' * 43
        action_token_provider = _SequenceActionTokenProvider(action_token)
        pending_handle_provider = _FixedPendingHandleProvider()
        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[IdentityPipe.get_action_token_provider] = lambda: (
            action_token_provider
        )
        app.dependency_overrides[
            IdentityPipe.get_pending_confirmation_handle_provider
        ] = lambda: pending_handle_provider

        with TestClient(
            app,
            headers={'x-shifu-bff-secret': ENVIRONMENT.bff_shared_secret},
        ) as client:
            registration = cast(
                'Response',
                client.post(  # pyright: ignore[reportUnknownMemberType]
                    '/identity/registrations',
                    json={
                        'display_name': 'Katherine Johnson',
                        'email': 'katherine@example.com',
                        'password': 'correct horse battery staple',
                    },
                ),
            )
            assert registration.status_code == 202

            response = cast(
                'Response',
                client.post(  # pyright: ignore[reportUnknownMemberType]
                    '/identity/email-confirmations',
                    json={'token': action_token},
                ),
            )

        assert response.status_code == 200
        body = response.json()
        assert body['result'] == 'activated'
        assert body['profile']['email'] == 'katherine@example.com'
        assert body['profile']['display_name'] == 'Katherine Johnson'
        assert body['access_version'] == 2

        database = SqlalchemyIdentityDatabase(engine=postgres_database.engine)
        with database.transaction() as repositories:
            account = repositories.accounts.find_non_deleted_by_email(
                'katherine@example.com'
            )
            assert account is not None
            assert account.status is AccountStatus.ACTIVE
            token_repository = cast(
                'ConfirmationAccountActionTokensRepository',
                repositories.account_action_tokens,
            )
            tokens = token_repository.find_many_by_account_id_and_type(
                account.id,
                AccountActionTokenType.EMAIL_CONFIRMATION,
            )
            assert len(tokens) == 1
            assert tokens[0].status is AccountActionTokenStatus.USED

    def test_malformed_token_is_rejected_before_use_case_execution(
        self,
        client: TestClient,
    ) -> None:
        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/email-confirmations',
                json={'token': 'malformed'},
            ),
        )

        assert response.status_code == 422
        assert response.json()['code'] == 'invalid_input'
