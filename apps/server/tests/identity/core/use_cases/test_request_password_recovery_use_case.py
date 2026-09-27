from datetime import UTC, datetime, timedelta
from unittest.mock import create_autospec

import pytest

from shifu.identity.core.domain.entities import Account, AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
    AccountStatus,
    ActionTokenDeliveryQueueStatus,
)
from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    IdentityDatabase,
    IdentityDatabaseRepositories,
    PasswordRecoveryDeliveryGateway,
    PasswordRecoveryDeliveryResult,
)
from shifu.identity.core.use_cases.request_password_recovery_use_case import (
    RequestPasswordRecoveryUseCase,
)
from shifu.fakers.identity.entities import AccountFaker
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class TestRequestPasswordRecoveryUseCase:
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
        self.id_provider.generate.side_effect = ['token-id', 'communication-id']
        self.action_token_provider.generate.return_value = 'raw-recovery-token'
        self.action_token_provider.hash.return_value = 'recovery-token-hash'
        self.handle_provider.generate.return_value = 'opaque-handle'
        self.handle_provider.hash.return_value = 'opaque-handle-hash'
        self.repositories.account_action_tokens.find_latest_by_account_id_and_type.return_value = None
        self.delivery_gateway.queue.return_value = PasswordRecoveryDeliveryResult(
            status=ActionTokenDeliveryQueueStatus.QUEUED
        )
        self.subject = RequestPasswordRecoveryUseCase(
            self.identity_database,
            self.id_provider,
            self.clock_provider,
            self.action_token_provider,
            self.handle_provider,
            self.delivery_gateway,
        )

    @pytest.mark.parametrize(
        'status',
        [AccountStatus.ACTIVE, AccountStatus.PENDING_CONFIRMATION],
    )
    def test_should_issue_one_recovery_token_for_eligible_account(
        self,
        status: AccountStatus,
    ) -> None:
        account = AccountFaker.fake(
            id='account-id',
            email='Learner@Example.com',
            status=status,
            created_at=self.now,
            updated_at=self.now,
            confirmed_at=self.now if status is AccountStatus.ACTIVE else None,
        )
        self.repositories.accounts.find_non_deleted_by_email.return_value = account
        self.repositories.account_action_tokens.find_many_pending_by_account_id_and_type.return_value = []

        result = self.subject.execute(' learner@example.com ')

        assert result.recovery_handle == 'opaque-handle'
        assert result.is_decoy is False
        token = self.repositories.account_action_tokens.add.call_args.args[0]
        assert token.account_id == account.id
        assert token.type is AccountActionTokenType.PASSWORD_RECOVERY
        assert token.token_hash == 'recovery-token-hash'
        assert token.pending_handle_hash == 'opaque-handle-hash'
        assert token.expires_at == self.now + timedelta(hours=1)
        queued_request = self.delivery_gateway.queue.call_args.args[0]
        assert queued_request.recipient_email == 'learner@example.com'
        assert queued_request.recovery_token == 'raw-recovery-token'
        self.repositories.accounts.find_non_deleted_by_email.assert_called_once_with(
            'learner@example.com'
        )

    @pytest.mark.parametrize(
        'account', [None, AccountFaker.fake(status=AccountStatus.DELETED)]
    )
    def test_should_return_decoy_without_protected_effects_for_unknown_or_deleted_account(
        self,
        account: Account | None,
    ) -> None:
        self.repositories.accounts.find_non_deleted_by_email.return_value = account

        result = self.subject.execute('missing@example.com')

        assert result.recovery_handle == 'opaque-handle'
        assert result.is_decoy is True
        self.repositories.account_action_tokens.add.assert_not_called()
        self.repositories.account_action_tokens.update.assert_not_called()
        self.repositories.events.add.assert_not_called()
        self.delivery_gateway.queue.assert_not_called()

    def test_should_return_decoy_without_replacement_during_cooldown(self) -> None:
        account = AccountFaker.fake(id='account-id', email='learner@example.com')
        latest_token = AccountActionToken(
            id='latest-token-id',
            account_id=account.id,
            type=AccountActionTokenType.PASSWORD_RECOVERY,
            status=AccountActionTokenStatus.PENDING,
            token_hash=self.token_hash,
            issued_at=self.now - timedelta(seconds=30),
            expires_at=self.now + timedelta(hours=1),
            updated_at=self.now - timedelta(seconds=30),
        )
        self.repositories.accounts.find_non_deleted_by_email.return_value = account
        self.repositories.account_action_tokens.find_latest_by_account_id_and_type.return_value = latest_token

        result = self.subject.execute(account.email)

        assert result.is_decoy is True
        self.repositories.account_action_tokens.add.assert_not_called()
        self.repositories.account_action_tokens.update.assert_not_called()
        self.delivery_gateway.queue.assert_not_called()

    def test_should_invalidate_pending_siblings_before_issuing_replacement(
        self,
    ) -> None:
        account = AccountFaker.fake(id='account-id', email='learner@example.com')
        sibling = AccountActionToken(
            id='sibling-token-id',
            account_id=account.id,
            type=AccountActionTokenType.PASSWORD_RECOVERY,
            status=AccountActionTokenStatus.PENDING,
            token_hash=self.token_hash,
            issued_at=self.now - timedelta(minutes=2),
            expires_at=self.now + timedelta(hours=1),
            updated_at=self.now - timedelta(minutes=2),
            communication_id='sibling-communication-id',
        )
        self.repositories.accounts.find_non_deleted_by_email.return_value = account
        self.repositories.account_action_tokens.find_many_pending_by_account_id_and_type.return_value = [
            sibling
        ]

        self.subject.execute(account.email)

        assert sibling.status is AccountActionTokenStatus.INVALIDATED
        assert sibling.invalidated_at == self.now
        assert (
            self.repositories.account_action_tokens.update.call_args_list[0].args[0]
            is sibling
        )
        cancellation = self.repositories.events.add.call_args.args[0]
        assert cancellation.payload.identity_action_token_id == sibling.id
        assert cancellation.payload.communication_id == sibling.communication_id
        assert cancellation.payload.reason.value == 'reissued'
