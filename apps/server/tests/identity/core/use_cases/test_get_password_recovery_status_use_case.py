from datetime import UTC, datetime, timedelta
from unittest.mock import create_autospec

import pytest

from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenCancellationReason,
    AccountActionTokenDeliveryStatus,
    AccountActionTokenStatus,
    AccountActionTokenType,
)
from shifu.identity.core.domain.events import (
    AccountActionTokenCancelledEvent,
    AccountActionTokenCancelledPayload,
)
from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    IdentityDatabase,
    IdentityDatabaseRepositories,
)
from shifu.identity.core.use_cases.get_password_recovery_status_use_case import (
    GetPasswordRecoveryStatusUseCase,
)
from shifu.fakers.identity.entities import AccountFaker
from shifu.shared.core.interfaces import ClockProvider


class TestGetPasswordRecoveryStatusUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.identity_database = create_autospec(IdentityDatabase, instance=True)
        self.repositories = create_autospec(IdentityDatabaseRepositories, instance=True)
        self.identity_database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.clock_provider = create_autospec(ClockProvider, instance=True)
        self.handle_provider = create_autospec(ActionTokenProvider, instance=True)
        self.now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        self.token_hash = 'token-hash'
        self.clock_provider.now.return_value = self.now
        self.handle_provider.hash.return_value = 'opaque-handle-hash'
        self.subject = GetPasswordRecoveryStatusUseCase(
            self.identity_database, self.clock_provider, self.handle_provider
        )

    def test_should_map_unknown_handle_to_opaque_delivery_issue(self) -> None:
        self.repositories.account_action_tokens.find_by_pending_handle_hash.return_value = None

        result = self.subject.execute('unknown-handle')

        assert result.state == 'delivery_issue'
        assert result.retry_after_seconds is None
        self.repositories.accounts.find_by_id.assert_not_called()

    @pytest.mark.parametrize(
        'delivery_status',
        [
            AccountActionTokenDeliveryStatus.DELIVERY_UNAVAILABLE,
            AccountActionTokenDeliveryStatus.PERMANENT_FAILURE,
            AccountActionTokenDeliveryStatus.EXHAUSTED,
        ],
    )
    def test_should_map_terminal_delivery_state_to_opaque_delivery_issue(
        self,
        delivery_status: AccountActionTokenDeliveryStatus,
    ) -> None:
        account = AccountFaker.fake(
            id='account-id', created_at=self.now, updated_at=self.now
        )
        token = AccountActionToken(
            id='token-id',
            account_id=account.id,
            type=AccountActionTokenType.PASSWORD_RECOVERY,
            status=AccountActionTokenStatus.PENDING,
            token_hash=self.token_hash,
            issued_at=self.now - timedelta(minutes=2),
            expires_at=self.now + timedelta(hours=1),
            updated_at=self.now,
            delivery_status=delivery_status,
        )
        self.repositories.account_action_tokens.find_by_pending_handle_hash.return_value = token
        self.repositories.accounts.find_by_id.return_value = account

        result = self.subject.execute('opaque-handle')

        assert result.state == 'delivery_issue'
        assert result.retry_after_seconds is None

    def test_should_return_cooldown_then_ready_without_disclosing_account(self) -> None:
        account = AccountFaker.fake(
            id='account-id', created_at=self.now, updated_at=self.now
        )
        token = AccountActionToken(
            id='token-id',
            account_id=account.id,
            type=AccountActionTokenType.PASSWORD_RECOVERY,
            status=AccountActionTokenStatus.PENDING,
            token_hash=self.token_hash,
            issued_at=self.now - timedelta(seconds=30),
            expires_at=self.now + timedelta(hours=1),
            updated_at=self.now,
        )
        self.repositories.account_action_tokens.find_by_pending_handle_hash.return_value = token
        self.repositories.accounts.find_by_id.return_value = account

        cooldown = self.subject.execute('opaque-handle')
        self.clock_provider.now.return_value = self.now + timedelta(seconds=60)
        ready = self.subject.execute('opaque-handle')

        assert (cooldown.state, cooldown.retry_after_seconds) == ('cooldown', 30)
        assert (ready.state, ready.retry_after_seconds) == ('ready', None)

    def test_should_expire_token_and_return_opaque_delivery_issue(self) -> None:
        account = AccountFaker.fake(
            id='account-id', created_at=self.now, updated_at=self.now
        )
        token = AccountActionToken(
            id='token-id',
            account_id=account.id,
            type=AccountActionTokenType.PASSWORD_RECOVERY,
            status=AccountActionTokenStatus.PENDING,
            token_hash=self.token_hash,
            issued_at=self.now - timedelta(hours=1),
            expires_at=self.now,
            updated_at=self.now - timedelta(hours=1),
            communication_id='communication-id',
        )
        self.repositories.account_action_tokens.find_by_pending_handle_hash.return_value = token
        self.repositories.accounts.find_by_id.return_value = account

        result = self.subject.execute('opaque-handle')

        assert result.state == 'delivery_issue'
        assert token.status is AccountActionTokenStatus.EXPIRED
        self.repositories.account_action_tokens.update.assert_called_once_with(token)
        self.repositories.events.add.assert_called_once_with(
            AccountActionTokenCancelledEvent(
                payload=AccountActionTokenCancelledPayload(
                    communication_id='communication-id',
                    identity_action_token_id=token.id,
                    reason=AccountActionTokenCancellationReason.EXPIRED,
                )
            )
        )
