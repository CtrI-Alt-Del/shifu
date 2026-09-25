from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
    AccountStatus,
)
from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    ConfirmationAccountActionTokensRepository,
    IdentityDatabase,
    IdentityDatabaseRepositories,
)
from shifu.identity.core.use_cases import IssuePendingConfirmationContextUseCase
from shifu.fakers.identity.entities import AccountFaker
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.interfaces import ClockProvider


CONFIRMATION_HASH = 'confirmation-secret-hash'


class TestIssuePendingConfirmationContextUseCase:
    @pytest.fixture(autouse=True)
    def setup_method(self) -> None:
        self.database = create_autospec(IdentityDatabase, instance=True)
        self.repositories = create_autospec(IdentityDatabaseRepositories, instance=True)
        self.token_repository = create_autospec(
            ConfirmationAccountActionTokensRepository,
            instance=True,
        )
        self.repositories.account_action_tokens = self.token_repository
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.clock_provider = create_autospec(ClockProvider, instance=True)
        self.pending_handle_provider = create_autospec(
            ActionTokenProvider,
            instance=True,
        )
        self.subject = IssuePendingConfirmationContextUseCase(
            identity_database=self.database,
            clock_provider=self.clock_provider,
            pending_confirmation_handle_provider=self.pending_handle_provider,
        )

    def test_should_replace_the_pending_handle_for_a_pending_account(self) -> None:
        now = datetime(2026, 9, 23, tzinfo=UTC)
        account = AccountFaker.fake(status=AccountStatus.PENDING_CONFIRMATION)
        token = AccountActionToken(
            id='01SHIFUPENDINGCONTEXT00001',
            account_id=account.id,
            type=AccountActionTokenType.EMAIL_CONFIRMATION,
            status=AccountActionTokenStatus.PENDING,
            token_hash=CONFIRMATION_HASH,
            issued_at=now,
            expires_at=now,
            updated_at=now,
            communication_id='01SHIFUPENDINGCONTEXT00002',
            pending_handle_hash='old-handle-hash',
        )
        self.clock_provider.now.return_value = now
        self.pending_handle_provider.generate.return_value = 'A' * 43
        self.pending_handle_provider.hash.return_value = 'new-handle-hash'
        self.repositories.accounts.find_by_id.return_value = account
        self.token_repository.find_latest_by_account_id_and_type.return_value = token

        result = self.subject.execute(account.id)

        assert result == 'A' * 43
        assert token.pending_handle_hash == 'new-handle-hash'
        assert token.updated_at == now
        self.token_repository.update.assert_called_once_with(token)

    def test_should_fail_safely_when_a_pending_account_has_no_confirmation_token(
        self,
    ) -> None:
        account = AccountFaker.fake(status=AccountStatus.PENDING_CONFIRMATION)
        self.repositories.accounts.find_by_id.return_value = account
        self.token_repository.find_latest_by_account_id_and_type.return_value = None

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute(account.id)

        self.token_repository.update.assert_not_called()
