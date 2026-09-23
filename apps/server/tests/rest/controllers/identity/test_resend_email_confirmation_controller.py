from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
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


class _MutableClockProvider:
    def __init__(self, current: datetime) -> None:
        self.current = current

    def now(self) -> datetime:
        return self.current


class TestResendEmailConfirmationController:
    def test_resend_observes_cooldown_without_creating_a_replacement(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        clock = _MutableClockProvider(datetime(2026, 1, 1, tzinfo=UTC))
        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[IdentityPipe.get_action_token_provider] = lambda: (
            _SequenceActionTokenProvider('A' * 43)
        )
        app.dependency_overrides[
            IdentityPipe.get_pending_confirmation_handle_provider
        ] = lambda: _FixedPendingHandleProvider()
        app.dependency_overrides[IdentityPipe.get_clock_provider] = lambda: clock

        with TestClient(
            app,
            headers={'x-shifu-bff-secret': ENVIRONMENT.bff_shared_secret},
        ) as client:
            registration = cast(
                'Response',
                client.post(  # pyright: ignore[reportUnknownMemberType]
                    '/identity/registrations',
                    json={
                        'display_name': 'Alan Turing',
                        'email': 'alan@example.com',
                        'password': 'correct horse battery staple',
                    },
                ),
            )
            pending_handle = registration.json()['pending_handle']

            response = cast(
                'Response',
                client.post(  # pyright: ignore[reportUnknownMemberType]
                    '/identity/pending-confirmations/resend',
                    json={'pending_handle': pending_handle},
                ),
            )

        assert response.status_code == 200
        assert response.json()['result'] == 'cooldown'
        assert response.json()['retry_after_seconds'] == 60

        database = SqlalchemyIdentityDatabase(engine=postgres_database.engine)
        with database.transaction() as repositories:
            account = repositories.accounts.find_non_deleted_by_email(
                'alan@example.com'
            )
            assert account is not None
            token_repository = cast(
                'ConfirmationAccountActionTokensRepository',
                repositories.account_action_tokens,
            )
            tokens = token_repository.find_many_by_account_id_and_type(
                account.id,
                AccountActionTokenType.EMAIL_CONFIRMATION,
            )
            assert len(tokens) == 1
            assert tokens[0].status is AccountActionTokenStatus.PENDING

    def test_eligible_resend_invalidates_old_token_and_accepts_new_delivery(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        clock = _MutableClockProvider(datetime(2026, 1, 1, tzinfo=UTC))
        action_token_provider = _SequenceActionTokenProvider('A' * 43, 'C' * 43)
        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[IdentityPipe.get_action_token_provider] = lambda: (
            action_token_provider
        )
        app.dependency_overrides[
            IdentityPipe.get_pending_confirmation_handle_provider
        ] = lambda: _FixedPendingHandleProvider()
        app.dependency_overrides[IdentityPipe.get_clock_provider] = lambda: clock

        with TestClient(
            app,
            headers={'x-shifu-bff-secret': ENVIRONMENT.bff_shared_secret},
        ) as client:
            registration = cast(
                'Response',
                client.post(  # pyright: ignore[reportUnknownMemberType]
                    '/identity/registrations',
                    json={
                        'display_name': 'Alan Turing',
                        'email': 'alan@example.com',
                        'password': 'correct horse battery staple',
                    },
                ),
            )
            pending_handle = registration.json()['pending_handle']
            clock.current += timedelta(seconds=61)

            response = cast(
                'Response',
                client.post(  # pyright: ignore[reportUnknownMemberType]
                    '/identity/pending-confirmations/resend',
                    json={'pending_handle': pending_handle},
                ),
            )

        assert response.status_code == 200
        assert response.json() == {'result': 'accepted', 'retry_after_seconds': None}

        database = SqlalchemyIdentityDatabase(engine=postgres_database.engine)
        with database.transaction() as repositories:
            account = repositories.accounts.find_non_deleted_by_email(
                'alan@example.com'
            )
            assert account is not None
            token_repository = cast(
                'ConfirmationAccountActionTokensRepository',
                repositories.account_action_tokens,
            )
            tokens = token_repository.find_many_by_account_id_and_type(
                account.id,
                AccountActionTokenType.EMAIL_CONFIRMATION,
            )
            assert len(tokens) == 2
            assert (
                sum(
                    token.status is AccountActionTokenStatus.INVALIDATED
                    for token in tokens
                )
                == 1
            )
            assert (
                sum(
                    token.status is AccountActionTokenStatus.PENDING for token in tokens
                )
                == 1
            )
