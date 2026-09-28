from datetime import UTC, datetime, timedelta
from unittest.mock import create_autospec

import pytest

from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
    AccountStatus,
)
from shifu.identity.core.domain.errors import InvalidPasswordError
from shifu.identity.core.domain.events import AccountPasswordRecoveredEvent
from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    IdentityDatabase,
    IdentityDatabaseRepositories,
    PasswordHashingProvider,
)
from shifu.identity.core.use_cases.reset_password_use_case import ResetPasswordUseCase
from shifu.fakers.identity.entities import AccountFaker
from shifu.shared.core.interfaces import ClockProvider


class TestResetPasswordUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.identity_database = create_autospec(IdentityDatabase, instance=True)
        self.repositories = create_autospec(IdentityDatabaseRepositories, instance=True)
        self.identity_database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.clock_provider = create_autospec(ClockProvider, instance=True)
        self.token_provider = create_autospec(ActionTokenProvider, instance=True)
        self.password_hashing_provider = create_autospec(
            PasswordHashingProvider, instance=True
        )
        self.now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        self.token_hash = 'token-hash'
        self.clock_provider.now.return_value = self.now
        self.token_provider.hash.return_value = 'token-hash'
        self.password_hashing_provider.hash.return_value = 'new-password-hash'
        self.subject = ResetPasswordUseCase(
            self.identity_database,
            self.clock_provider,
            self.token_provider,
            self.password_hashing_provider,
        )

    def test_should_reset_pending_account_and_invalidate_recovery_siblings(
        self,
    ) -> None:
        account = AccountFaker.fake(
            id='account-id',
            status=AccountStatus.PENDING_CONFIRMATION,
            access_version=4,
            created_at=self.now,
            updated_at=self.now,
            confirmed_at=None,
        )
        current = AccountActionToken(
            id='current-id',
            account_id=account.id,
            type=AccountActionTokenType.PASSWORD_RECOVERY,
            status=AccountActionTokenStatus.PENDING,
            token_hash=self.token_hash,
            issued_at=self.now - timedelta(minutes=1),
            expires_at=self.now + timedelta(hours=1),
            updated_at=self.now,
            communication_id='current-communication-id',
        )
        sibling = AccountActionToken(
            id='sibling-id',
            account_id=account.id,
            type=AccountActionTokenType.PASSWORD_RECOVERY,
            status=AccountActionTokenStatus.PENDING,
            token_hash=self.token_hash,
            issued_at=self.now - timedelta(minutes=2),
            expires_at=self.now + timedelta(hours=1),
            updated_at=self.now,
            communication_id='sibling-communication-id',
        )
        self.repositories.account_action_tokens.find_by_hash.return_value = current
        self.repositories.accounts.find_by_id.return_value = account
        self.repositories.account_action_tokens.find_many_pending_by_account_id_and_type.return_value = [
            sibling
        ]

        result = self.subject.execute('raw-token', 'new-password', 'new-password')

        assert result.result == 'reset'
        assert result.account_id == account.id
        assert result.requires_email_confirmation is True
        assert result.access_version == 5
        assert account.status is AccountStatus.PENDING_CONFIRMATION
        assert account.password_hash == 'new-password-hash'
        assert current.status is AccountActionTokenStatus.USED
        assert sibling.status is AccountActionTokenStatus.INVALIDATED
        self.repositories.accounts.update.assert_called_once_with(account)
        events = [call.args[0] for call in self.repositories.events.add.call_args_list]
        recovered = next(
            event
            for event in events
            if isinstance(event, AccountPasswordRecoveredEvent)
        )
        assert recovered.payload.account_id == account.id
        assert recovered.payload.access_version == 5

    @pytest.mark.parametrize(
        ('status', 'expected'),
        [
            (AccountActionTokenStatus.USED, 'used'),
            (AccountActionTokenStatus.EXPIRED, 'expired'),
            (AccountActionTokenStatus.INVALIDATED, 'invalid'),
        ],
    )
    def test_should_map_terminal_or_invalid_token_without_account_effects(
        self,
        status: AccountActionTokenStatus,
        expected: str,
    ) -> None:
        token = AccountActionToken(
            id='token-id',
            account_id='account-id',
            type=AccountActionTokenType.PASSWORD_RECOVERY,
            status=status,
            token_hash=self.token_hash,
            issued_at=self.now - timedelta(hours=2),
            expires_at=self.now - timedelta(hours=1),
            updated_at=self.now,
        )
        self.repositories.account_action_tokens.find_by_hash.return_value = token

        result = self.subject.execute('raw-token', 'new-password', 'new-password')

        assert result.result == expected
        self.repositories.accounts.find_by_id.assert_not_called()
        self.repositories.accounts.update.assert_not_called()
        self.password_hashing_provider.hash.assert_not_called()

    def test_should_expire_pending_token_without_password_or_access_effects(
        self,
    ) -> None:
        token = AccountActionToken(
            id='token-id',
            account_id='account-id',
            type=AccountActionTokenType.PASSWORD_RECOVERY,
            status=AccountActionTokenStatus.PENDING,
            token_hash=self.token_hash,
            issued_at=self.now - timedelta(hours=1),
            expires_at=self.now,
            updated_at=self.now - timedelta(hours=1),
        )
        self.repositories.account_action_tokens.find_by_hash.return_value = token

        result = self.subject.execute('raw-token', 'new-password', 'new-password')

        assert result.result == 'expired'
        assert token.status is AccountActionTokenStatus.EXPIRED
        self.repositories.accounts.find_by_id.assert_not_called()
        self.password_hashing_provider.hash.assert_not_called()

    @pytest.mark.parametrize(
        'password, confirmation',
        [('short', 'short'), ('password-one', 'password-two')],
    )
    def test_should_reject_invalid_password_without_token_or_account_effects(
        self,
        password: str,
        confirmation: str,
    ) -> None:
        with pytest.raises(InvalidPasswordError):
            self.subject.execute('raw-token', password, confirmation)

        self.identity_database.transaction.assert_not_called()
        self.token_provider.hash.assert_not_called()
        self.password_hashing_provider.hash.assert_not_called()
