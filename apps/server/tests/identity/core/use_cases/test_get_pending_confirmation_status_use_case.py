from datetime import UTC, datetime, timedelta
from unittest.mock import create_autospec

import pytest

from shifu.fakers.identity.entities import AccountFaker
from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenDeliveryStatus,
    AccountActionTokenStatus,
    AccountActionTokenType,
    AccountStatus,
)
from shifu.identity.core.domain.structures import PendingConfirmationStatusResult
from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    IdentityDatabase,
    IdentityDatabaseRepositories,
)
from shifu.identity.core.use_cases import GetPendingConfirmationStatusUseCase
from shifu.shared.core.interfaces import ClockProvider


class TestGetPendingConfirmationStatusUseCase:
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
        self.pending_handle_provider = create_autospec(
            ActionTokenProvider,
            instance=True,
        )
        self.now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        self.clock_provider.now.return_value = self.now
        self.pending_handle_provider.hash.return_value = 'pending-handle-hash'
        self.account = AccountFaker.fake(status=AccountStatus.PENDING_CONFIRMATION)
        self.repositories.accounts.find_by_id.return_value = self.account
        self.subject = GetPendingConfirmationStatusUseCase(
            identity_database=self.identity_database,
            clock_provider=self.clock_provider,
            pending_confirmation_handle_provider=self.pending_handle_provider,
        )

    def _token(
        self,
        *,
        issued_ago: timedelta,
        status: AccountActionTokenStatus = AccountActionTokenStatus.PENDING,
        delivery_status: AccountActionTokenDeliveryStatus | None = None,
    ) -> AccountActionToken:
        issued_at = self.now - issued_ago
        return AccountActionToken(
            id='01JTOKEN0000000000000000001',
            account_id=self.account.id,
            type=AccountActionTokenType.EMAIL_CONFIRMATION,
            status=status,
            token_hash='token-hash',  # noqa: S106
            issued_at=issued_at,
            expires_at=issued_at + timedelta(hours=24),
            updated_at=issued_at,
            communication_id='01JCOMMUNICATION000000000001',
            pending_handle_hash='pending-handle-hash',
            delivery_status=delivery_status,
        )

    def test_should_report_delivery_issue_when_handle_is_unknown(self) -> None:
        tokens = self.repositories.account_action_tokens
        tokens.find_by_pending_handle_hash.return_value = None

        result = self.subject.execute('unknown-handle')

        assert result == PendingConfirmationStatusResult(state='delivery_issue')
        self.pending_handle_provider.hash.assert_called_once_with('unknown-handle')
        self.repositories.accounts.find_by_id.assert_not_called()

    @pytest.mark.parametrize(
        'account_status', [AccountStatus.ACTIVE, AccountStatus.DELETED]
    )
    def test_should_report_delivery_issue_when_account_is_not_pending(
        self,
        account_status: AccountStatus,
    ) -> None:
        tokens = self.repositories.account_action_tokens
        tokens.find_by_pending_handle_hash.return_value = self._token(
            issued_ago=timedelta(minutes=5)
        )
        self.repositories.accounts.find_by_id.return_value = AccountFaker.fake(
            status=account_status
        )

        result = self.subject.execute('handle')

        assert result == PendingConfirmationStatusResult(state='delivery_issue')
        tokens.find_latest_by_account_id_and_type.assert_not_called()

    def test_should_report_delivery_issue_when_account_is_missing(self) -> None:
        tokens = self.repositories.account_action_tokens
        tokens.find_by_pending_handle_hash.return_value = self._token(
            issued_ago=timedelta(minutes=5)
        )
        self.repositories.accounts.find_by_id.return_value = None

        result = self.subject.execute('handle')

        assert result == PendingConfirmationStatusResult(state='delivery_issue')

    def test_should_report_delivery_issue_when_latest_token_is_not_pending(
        self,
    ) -> None:
        tokens = self.repositories.account_action_tokens
        tokens.find_by_pending_handle_hash.return_value = self._token(
            issued_ago=timedelta(minutes=5)
        )
        tokens.find_latest_by_account_id_and_type.return_value = self._token(
            issued_ago=timedelta(seconds=10),
            status=AccountActionTokenStatus.INVALIDATED,
        )

        result = self.subject.execute('handle')

        assert result == PendingConfirmationStatusResult(state='delivery_issue')
        tokens.find_latest_by_account_id_and_type.assert_called_once_with(
            self.account.id,
            AccountActionTokenType.EMAIL_CONFIRMATION,
        )

    @pytest.mark.parametrize(
        'delivery_status',
        [
            AccountActionTokenDeliveryStatus.DELIVERY_UNAVAILABLE,
            AccountActionTokenDeliveryStatus.TEMPORARY_FAILURE,
            AccountActionTokenDeliveryStatus.PERMANENT_FAILURE,
            AccountActionTokenDeliveryStatus.EXHAUSTED,
        ],
    )
    def test_should_report_delivery_issue_for_failed_delivery_states(
        self,
        delivery_status: AccountActionTokenDeliveryStatus,
    ) -> None:
        tokens = self.repositories.account_action_tokens
        token = self._token(
            issued_ago=timedelta(seconds=5),
            delivery_status=delivery_status,
        )
        tokens.find_by_pending_handle_hash.return_value = token
        tokens.find_latest_by_account_id_and_type.return_value = token

        result = self.subject.execute('handle')

        assert result == PendingConfirmationStatusResult(state='delivery_issue')

    def test_should_report_cooldown_with_remaining_seconds_rounded_up(self) -> None:
        tokens = self.repositories.account_action_tokens
        token = self._token(issued_ago=timedelta(seconds=45, milliseconds=500))
        tokens.find_by_pending_handle_hash.return_value = token
        tokens.find_latest_by_account_id_and_type.return_value = token

        result = self.subject.execute('handle')

        assert result == PendingConfirmationStatusResult(
            state='cooldown',
            retry_after_seconds=15,
        )

    def test_should_fall_back_to_the_handle_token_when_no_latest_token_exists(
        self,
    ) -> None:
        tokens = self.repositories.account_action_tokens
        tokens.find_by_pending_handle_hash.return_value = self._token(
            issued_ago=timedelta(seconds=59, milliseconds=999)
        )
        tokens.find_latest_by_account_id_and_type.return_value = None

        result = self.subject.execute('handle')

        assert result == PendingConfirmationStatusResult(
            state='cooldown',
            retry_after_seconds=1,
        )

    @pytest.mark.parametrize('issued_ago', [timedelta(seconds=60), timedelta(hours=1)])
    def test_should_report_ready_once_the_cooldown_has_elapsed(
        self,
        issued_ago: timedelta,
    ) -> None:
        tokens = self.repositories.account_action_tokens
        token = self._token(
            issued_ago=issued_ago,
            delivery_status=AccountActionTokenDeliveryStatus.QUEUED,
        )
        tokens.find_by_pending_handle_hash.return_value = token
        tokens.find_latest_by_account_id_and_type.return_value = token

        result = self.subject.execute('handle')

        assert result == PendingConfirmationStatusResult(state='ready')
        tokens.update.assert_not_called()
