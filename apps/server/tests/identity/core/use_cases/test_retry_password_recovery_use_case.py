from datetime import UTC, datetime, timedelta
from unittest.mock import create_autospec

import pytest

from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenDeliveryStatus,
    AccountActionTokenStatus,
    AccountActionTokenType,
    ActionTokenDeliveryQueueStatus,
)
from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    IdentityDatabase,
    IdentityDatabaseRepositories,
    PasswordRecoveryDeliveryGateway,
    PasswordRecoveryDeliveryResult,
)
from shifu.identity.core.use_cases.retry_password_recovery_use_case import (
    RetryPasswordRecoveryUseCase,
)
from shifu.fakers.identity.entities import AccountFaker
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class TestRetryPasswordRecoveryUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.identity_database = create_autospec(IdentityDatabase, instance=True)
        self.repositories = create_autospec(IdentityDatabaseRepositories, instance=True)
        self.identity_database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.id_provider = create_autospec(IdentifierProvider, instance=True)
        self.clock_provider = create_autospec(ClockProvider, instance=True)
        self.action_token_provider = create_autospec(ActionTokenProvider, instance=True)
        self.handle_provider = create_autospec(ActionTokenProvider, instance=True)
        self.delivery_gateway = create_autospec(
            PasswordRecoveryDeliveryGateway, instance=True
        )
        self.now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        self.token_hash = 'token-hash'
        self.clock_provider.now.return_value = self.now
        self.handle_provider.hash.return_value = 'opaque-handle-hash'
        self.id_provider.generate.side_effect = ['replacement-id', 'communication-id']
        self.action_token_provider.generate.return_value = 'replacement-token'
        self.action_token_provider.hash.return_value = 'replacement-token-hash'
        self.delivery_gateway.queue.return_value = PasswordRecoveryDeliveryResult(
            status=ActionTokenDeliveryQueueStatus.QUEUED
        )
        self.subject = RetryPasswordRecoveryUseCase(
            self.identity_database,
            self.id_provider,
            self.clock_provider,
            self.action_token_provider,
            self.handle_provider,
            self.delivery_gateway,
        )

    def test_should_replace_token_after_terminal_delivery_issue(self) -> None:
        account = AccountFaker.fake(id='account-id', email='learner@example.com')
        failed = AccountActionToken(
            id='failed-id',
            account_id=account.id,
            type=AccountActionTokenType.PASSWORD_RECOVERY,
            status=AccountActionTokenStatus.PENDING,
            token_hash=self.token_hash,
            issued_at=self.now - timedelta(minutes=2),
            expires_at=self.now + timedelta(hours=1),
            updated_at=self.now,
            communication_id='failed-communication-id',
            pending_handle_hash='opaque-handle-hash',
            delivery_status=AccountActionTokenDeliveryStatus.PERMANENT_FAILURE,
        )
        self.repositories.account_action_tokens.find_by_pending_handle_hash.return_value = failed
        self.repositories.accounts.find_by_id.return_value = account
        self.repositories.account_action_tokens.find_many_pending_by_account_id_and_type.return_value = [
            failed
        ]

        result = self.subject.execute('opaque-handle')

        assert result.is_decoy is False
        assert failed.status is AccountActionTokenStatus.INVALIDATED
        replacement = self.repositories.account_action_tokens.add.call_args.args[0]
        assert replacement.id == 'replacement-id'
        assert replacement.pending_handle_hash == 'opaque-handle-hash'
        self.delivery_gateway.queue.assert_called_once()

    def test_should_keep_nonterminal_context_generic_without_reissuing(self) -> None:
        account = AccountFaker.fake(id='account-id')
        token = AccountActionToken(
            id='token-id',
            account_id=account.id,
            type=AccountActionTokenType.PASSWORD_RECOVERY,
            status=AccountActionTokenStatus.PENDING,
            token_hash=self.token_hash,
            issued_at=self.now,
            expires_at=self.now + timedelta(hours=1),
            updated_at=self.now,
            pending_handle_hash='opaque-handle-hash',
            delivery_status=AccountActionTokenDeliveryStatus.QUEUED,
        )
        self.repositories.account_action_tokens.find_by_pending_handle_hash.return_value = token
        self.repositories.accounts.find_by_id.return_value = account

        result = self.subject.execute('opaque-handle')

        assert result.is_decoy is False
        self.repositories.account_action_tokens.add.assert_not_called()
        self.delivery_gateway.queue.assert_not_called()

    def test_should_return_decoy_without_protected_effects_for_unknown_context(
        self,
    ) -> None:
        self.repositories.account_action_tokens.find_by_pending_handle_hash.return_value = None

        result = self.subject.execute('unknown-handle')

        assert result.recovery_handle == 'unknown-handle'
        assert result.is_decoy is True
        self.repositories.accounts.find_by_id.assert_not_called()
        self.repositories.account_action_tokens.add.assert_not_called()
        self.delivery_gateway.queue.assert_not_called()

    def test_should_expire_context_without_replacement_when_retry_is_too_late(
        self,
    ) -> None:
        account = AccountFaker.fake(id='account-id')
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
            pending_handle_hash='opaque-handle-hash',
            delivery_status=AccountActionTokenDeliveryStatus.PERMANENT_FAILURE,
        )
        self.repositories.account_action_tokens.find_by_pending_handle_hash.return_value = token
        self.repositories.accounts.find_by_id.return_value = account

        result = self.subject.execute('opaque-handle')

        assert result.is_decoy is True
        assert token.status is AccountActionTokenStatus.EXPIRED
        self.repositories.account_action_tokens.add.assert_not_called()
        self.delivery_gateway.queue.assert_not_called()
