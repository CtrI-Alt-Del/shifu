from datetime import UTC, datetime, timedelta
from unittest.mock import create_autospec

import pytest

from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
    AccountConfirmationCancellationReason,
    AccountDeletionReason,
    AccountStatus,
)
from shifu.identity.core.domain.events import (
    AccountConfirmationCancelledEvent,
    AccountExpiredEvent,
    AccountExpiryRequestedEvent,
)
from shifu.identity.core.interfaces import (
    IdentityDatabase,
    IdentityDatabaseRepositories,
)
from shifu.identity.core.use_cases.expire_unconfirmed_accounts_use_case import (
    ExpireUnconfirmedAccountsUseCase,
)
from shifu.fakers.identity.entities import AccountFaker
from shifu.shared.core.interfaces import ClockProvider


class TestExpireUnconfirmedAccountsUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.identity_database = create_autospec(IdentityDatabase, instance=True)
        self.repositories = create_autospec(
            IdentityDatabaseRepositories,
            instance=True,
        )
        self.identity_database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.clock_provider = create_autospec(ClockProvider, instance=True)
        self.now = datetime(2026, 1, 8, 12, 0, tzinfo=UTC)
        self.clock_provider.now.return_value = self.now
        self.subject = ExpireUnconfirmedAccountsUseCase(
            self.identity_database,
            self.clock_provider,
        )

    def test_should_expire_at_seven_day_boundary_and_cancel_all_related_delivery(
        self,
    ) -> None:
        account = AccountFaker.fake(
            id='01JACCOUNT000000000000000001',
            status=AccountStatus.PENDING_CONFIRMATION,
            access_version=4,
            created_at=self.now - timedelta(days=7),
            updated_at=self.now - timedelta(days=7),
            confirmed_at=None,
        )
        pending_token = AccountActionToken(
            id='01JPENDINGTOKEN000000000000001',
            account_id=account.id,
            type=AccountActionTokenType.EMAIL_CONFIRMATION,
            status=AccountActionTokenStatus.PENDING,
            token_hash='pending-token-hash',  # noqa: S106
            issued_at=self.now - timedelta(days=6),
            expires_at=self.now + timedelta(hours=18),
            updated_at=self.now - timedelta(days=6),
            communication_id='01JPENDINGCOMMUNICATION00000001',
        )
        invalidated_token = AccountActionToken(
            id='01JINVALIDATEDTOKEN00000000001',
            account_id=account.id,
            type=AccountActionTokenType.EMAIL_CONFIRMATION,
            status=AccountActionTokenStatus.INVALIDATED,
            token_hash='invalidated-token-hash',  # noqa: S106
            issued_at=self.now - timedelta(days=5),
            expires_at=self.now + timedelta(hours=19),
            updated_at=self.now - timedelta(days=5),
            communication_id='01JINVALIDATEDCOMMUNICATION000001',
        )
        self.repositories.accounts.find_by_id.return_value = account
        self.repositories.account_action_tokens.find_many_by_account_id_and_type.return_value = [
            pending_token,
            invalidated_token,
        ]

        result = self.subject.execute(account.id)

        assert result == (account.id,)
        assert account.status is AccountStatus.DELETED
        assert account.deleted_at == self.now
        assert (
            account.deletion_reason is AccountDeletionReason.UNCONFIRMED_ACCOUNT_EXPIRED
        )
        assert account.access_version == 5
        assert pending_token.status is AccountActionTokenStatus.EXPIRED
        assert pending_token.updated_at == self.now
        assert invalidated_token.status is AccountActionTokenStatus.INVALIDATED
        assert self.repositories.accounts.update.call_args.args[0] is account
        assert (
            self.repositories.account_action_tokens.update.call_args.args[0]
            is pending_token
        )

        events = [call.args[0] for call in self.repositories.events.add.call_args_list]
        cancellation_events = [
            event
            for event in events
            if isinstance(event, AccountConfirmationCancelledEvent)
        ]
        assert {event.payload.communication_id for event in cancellation_events} == {
            pending_token.communication_id,
            invalidated_token.communication_id,
        }
        assert all(
            event.payload.reason is AccountConfirmationCancellationReason.EXPIRED
            for event in cancellation_events
        )
        expired_event = next(
            event for event in events if isinstance(event, AccountExpiredEvent)
        )
        assert expired_event.payload.account_id == account.id
        assert expired_event.payload.expired_at == self.now.isoformat()

    def test_should_claim_at_most_one_hundred_ids_for_independent_expiry_events(
        self,
    ) -> None:
        accounts = [
            AccountFaker.fake(
                id='01JACCOUNT000000000000000001',
                status=AccountStatus.PENDING_CONFIRMATION,
                created_at=self.now - timedelta(days=7),
                updated_at=self.now - timedelta(days=7),
                confirmed_at=None,
            ),
            AccountFaker.fake(
                id='01JACCOUNT000000000000000002',
                status=AccountStatus.PENDING_CONFIRMATION,
                created_at=self.now - timedelta(days=8),
                updated_at=self.now - timedelta(days=8),
                confirmed_at=None,
            ),
        ]
        self.repositories.accounts.find_many_pending_created_before.return_value = (
            accounts
        )

        result = self.subject.execute()

        assert result == tuple(account.id for account in accounts)
        self.repositories.accounts.find_many_pending_created_before.assert_called_once_with(
            self.now - timedelta(days=7),
            limit=100,
        )
        self.repositories.accounts.update.assert_not_called()
        self.repositories.account_action_tokens.update.assert_not_called()
        events = [call.args[0] for call in self.repositories.events.add.call_args_list]
        assert all(isinstance(event, AccountExpiryRequestedEvent) for event in events)
        assert [event.payload.account_id for event in events] == [
            account.id for account in accounts
        ]

    def test_should_ignore_younger_or_already_deleted_accounts(self) -> None:
        account = AccountFaker.fake(
            status=AccountStatus.PENDING_CONFIRMATION,
            created_at=self.now - timedelta(days=6, seconds=1),
            updated_at=self.now - timedelta(days=6, seconds=1),
            confirmed_at=None,
        )
        self.repositories.accounts.find_by_id.return_value = account

        assert self.subject.execute(account.id) == ()
        self.repositories.accounts.update.assert_not_called()
        self.repositories.account_action_tokens.find_many_by_account_id_and_type.assert_not_called()
        self.repositories.events.add.assert_not_called()
