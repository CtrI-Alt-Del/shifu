from datetime import UTC, datetime, timedelta
from unittest.mock import create_autospec

import pytest

from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
)
from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    IdentityDatabase,
    IdentityDatabaseRepositories,
)
from shifu.identity.core.use_cases import ResolvePasswordResetLinkUseCase
from shifu.shared.core.interfaces import ClockProvider


_TOKEN_HASH = 'token-hash'


class TestResolvePasswordResetLinkUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.identity_database = create_autospec(IdentityDatabase, instance=True)
        self.repositories = create_autospec(IdentityDatabaseRepositories, instance=True)
        self.identity_database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.clock_provider = create_autospec(ClockProvider, instance=True)
        self.action_token_provider = create_autospec(ActionTokenProvider, instance=True)
        self.now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        self.token = 'A' * 43
        self.clock_provider.now.return_value = self.now
        self.action_token_provider.hash.return_value = _TOKEN_HASH
        self.subject = ResolvePasswordResetLinkUseCase(
            identity_database=self.identity_database,
            clock_provider=self.clock_provider,
            action_token_provider=self.action_token_provider,
        )

    def test_should_resolve_a_pending_unexpired_recovery_token_as_valid(self) -> None:
        action_token = self._action_token()
        self.repositories.account_action_tokens.find_by_hash.return_value = action_token

        result = self.subject.execute(self.token)

        assert result.result == 'valid'
        self.repositories.account_action_tokens.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

    @pytest.mark.parametrize(
        ('token_status', 'expires_at', 'expected_result'),
        [
            (AccountActionTokenStatus.USED, timedelta(hours=1), 'used'),
            (AccountActionTokenStatus.EXPIRED, timedelta(hours=-1), 'expired'),
            (AccountActionTokenStatus.INVALIDATED, timedelta(hours=1), 'invalid'),
            (AccountActionTokenStatus.PENDING, timedelta(), 'expired'),
        ],
    )
    def test_should_resolve_terminal_or_expired_tokens_without_mutation(
        self,
        token_status: AccountActionTokenStatus,
        expires_at: timedelta,
        expected_result: str,
    ) -> None:
        action_token = self._action_token(
            status=token_status,
            expires_at=self.now + expires_at,
        )
        self.repositories.account_action_tokens.find_by_hash.return_value = action_token

        result = self.subject.execute(self.token)

        assert result.result == expected_result
        assert action_token.status is token_status
        self.repositories.account_action_tokens.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_return_invalid_without_side_effects_for_malformed_token(
        self,
    ) -> None:
        result = self.subject.execute('malformed token')

        assert result.result == 'invalid'
        self.action_token_provider.hash.assert_not_called()
        self.clock_provider.now.assert_not_called()
        self.identity_database.transaction.assert_not_called()

    def test_should_return_invalid_for_an_unknown_or_non_recovery_token(self) -> None:
        self.repositories.account_action_tokens.find_by_hash.return_value = None

        unknown_result = self.subject.execute(self.token)

        self.repositories.account_action_tokens.find_by_hash.return_value = (
            self._action_token(type=AccountActionTokenType.EMAIL_CONFIRMATION)
        )
        confirmation_result = self.subject.execute(self.token)

        assert unknown_result.result == confirmation_result.result == 'invalid'
        self.repositories.account_action_tokens.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def _action_token(
        self,
        *,
        type: AccountActionTokenType = AccountActionTokenType.PASSWORD_RECOVERY,
        status: AccountActionTokenStatus = AccountActionTokenStatus.PENDING,
        expires_at: datetime | None = None,
    ) -> AccountActionToken:
        return AccountActionToken(
            id='token-id',
            account_id='account-id',
            type=type,
            status=status,
            token_hash=_TOKEN_HASH,
            issued_at=self.now - timedelta(minutes=1),
            expires_at=expires_at or self.now + timedelta(hours=1),
            updated_at=self.now,
        )
