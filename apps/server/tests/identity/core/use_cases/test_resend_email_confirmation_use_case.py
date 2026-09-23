from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast
from unittest.mock import create_autospec

import pytest

from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
    AccountConfirmationCancellationReason,
    AccountStatus,
    ResendConfirmationResultStatus,
)
from shifu.identity.core.domain.structures import ResendConfirmationResult
from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    IdentityDatabase,
    IdentityDatabaseRepositories,
)
from shifu.identity.core.use_cases.resend_email_confirmation_use_case import (
    ResendEmailConfirmationUseCase,
)
from shifu.fakers.identity.entities import AccountFaker
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider

if TYPE_CHECKING:
    from shifu.identity.core.domain.events import AccountConfirmationCancelledEvent


class TestResendEmailConfirmationUseCase:
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
        self.id_provider = create_autospec(IdentifierProvider, instance=True)
        self.clock_provider = create_autospec(ClockProvider, instance=True)
        self.action_token_provider = create_autospec(
            ActionTokenProvider,
            instance=True,
        )
        self.pending_handle_provider = create_autospec(
            ActionTokenProvider,
            instance=True,
        )
        self.now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        self.clock_provider.now.return_value = self.now
        self.pending_handle_provider.hash.return_value = 'pending-handle-hash'
        self.action_token_provider.generate.return_value = 'replacement-token'
        self.action_token_provider.hash.return_value = 'replacement-token-hash'
        self.id_provider.generate.side_effect = [
            '01JREPLACEMENT000000000001',
            '01JCOMMUNICATION000000000002',
        ]
        self.subject = ResendEmailConfirmationUseCase(
            self.identity_database,
            self.id_provider,
            self.clock_provider,
            self.action_token_provider,
            self.pending_handle_provider,
        )

    def test_should_replace_pending_token_after_cooldown_and_cancel_old_delivery(
        self,
    ) -> None:
        account = AccountFaker.fake(
            id='01JACCOUNT000000000000000001',
            status=AccountStatus.PENDING_CONFIRMATION,
            created_at=self.now - timedelta(hours=1),
            updated_at=self.now - timedelta(hours=1),
            confirmed_at=None,
        )
        old_token = AccountActionToken(
            id='01JOLDTOKEN00000000000000001',
            account_id=account.id,
            type=AccountActionTokenType.EMAIL_CONFIRMATION,
            status=AccountActionTokenStatus.PENDING,
            token_hash='old-token-hash',  # noqa: S106
            issued_at=self.now - timedelta(seconds=61),
            expires_at=self.now + timedelta(hours=23),
            updated_at=self.now - timedelta(seconds=61),
            communication_id='01JOLDCOMMUNICATION00000000001',
            pending_handle_hash='pending-handle-hash',
        )
        self.repositories.account_action_tokens.find_by_pending_handle_hash.return_value = old_token
        self.repositories.accounts.find_by_id.return_value = account
        self.repositories.account_action_tokens.find_latest_by_account_id_and_type.return_value = old_token
        self.repositories.account_action_tokens.find_many_pending_by_account_id_and_type.return_value = [
            old_token
        ]

        result = self.subject.execute('pending-handle')

        assert result.result is ResendConfirmationResultStatus.ACCEPTED
        assert result.identity_confirmation_id == '01JREPLACEMENT000000000001'
        assert result.communication_id == '01JCOMMUNICATION000000000002'
        assert result.confirmation_token == 'replacement-token'
        assert result.confirmation_expires_at == self.now + timedelta(hours=24)
        assert old_token.status is AccountActionTokenStatus.INVALIDATED
        replacement_token = self.repositories.account_action_tokens.add.call_args.args[
            0
        ]
        assert replacement_token.account_id == account.id
        assert replacement_token.pending_handle_hash == 'pending-handle-hash'
        assert replacement_token.token_hash == 'replacement-token-hash'
        assert replacement_token.id == result.identity_confirmation_id
        assert replacement_token.communication_id == result.communication_id

        cancellation_event = cast(
            'AccountConfirmationCancelledEvent',
            self.repositories.events.add.call_args.args[0],
        )
        assert cancellation_event.payload.communication_id == old_token.communication_id
        assert cancellation_event.payload.identity_confirmation_id == old_token.id
        assert (
            cancellation_event.payload.reason
            is AccountConfirmationCancellationReason.REISSUED
        )

    def test_should_return_cooldown_without_creating_replacement(self) -> None:
        account = AccountFaker.fake(
            status=AccountStatus.PENDING_CONFIRMATION,
            created_at=self.now - timedelta(hours=1),
            updated_at=self.now - timedelta(hours=1),
            confirmed_at=None,
        )
        latest_token = AccountActionToken(
            id='01JOLDTOKEN00000000000000001',
            account_id=account.id,
            type=AccountActionTokenType.EMAIL_CONFIRMATION,
            status=AccountActionTokenStatus.PENDING,
            token_hash='old-token-hash',  # noqa: S106
            issued_at=self.now - timedelta(seconds=30),
            expires_at=self.now + timedelta(hours=23),
            updated_at=self.now - timedelta(seconds=30),
            pending_handle_hash='pending-handle-hash',
        )
        self.repositories.account_action_tokens.find_by_pending_handle_hash.return_value = latest_token
        self.repositories.accounts.find_by_id.return_value = account
        self.repositories.account_action_tokens.find_latest_by_account_id_and_type.return_value = latest_token

        result = self.subject.execute('pending-handle')

        assert result == ResendConfirmationResult(
            result=ResendConfirmationResultStatus.COOLDOWN,
            retry_after_seconds=30,
        )
        self.id_provider.generate.assert_not_called()
        self.action_token_provider.generate.assert_not_called()
        self.repositories.account_action_tokens.update.assert_not_called()
        self.repositories.account_action_tokens.add.assert_not_called()
        self.repositories.events.add.assert_not_called()

    @pytest.mark.parametrize('account_status', [None, AccountStatus.ACTIVE])
    def test_should_keep_unknown_or_ineligible_handle_generic(
        self,
        account_status: AccountStatus | None,
    ) -> None:
        if account_status is None:
            self.repositories.account_action_tokens.find_by_pending_handle_hash.return_value = None
        else:
            token = AccountActionToken(
                id='01JOLDTOKEN00000000000000001',
                account_id='01JACCOUNT000000000000000001',
                type=AccountActionTokenType.EMAIL_CONFIRMATION,
                status=AccountActionTokenStatus.PENDING,
                token_hash='old-token-hash',  # noqa: S106
                issued_at=self.now - timedelta(minutes=2),
                expires_at=self.now + timedelta(hours=23),
                updated_at=self.now - timedelta(minutes=2),
                pending_handle_hash='pending-handle-hash',
            )
            self.repositories.account_action_tokens.find_by_pending_handle_hash.return_value = token
            self.repositories.accounts.find_by_id.return_value = AccountFaker.fake(
                id=token.account_id,
                status=account_status,
            )

        result = self.subject.execute('unknown-or-ineligible-handle')

        assert result == ResendConfirmationResult(
            result=ResendConfirmationResultStatus.ACCEPTED
        )
        self.id_provider.generate.assert_not_called()
        self.action_token_provider.generate.assert_not_called()
        self.repositories.account_action_tokens.add.assert_not_called()
        self.repositories.events.add.assert_not_called()
