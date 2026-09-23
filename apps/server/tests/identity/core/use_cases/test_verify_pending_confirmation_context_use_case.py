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
from shifu.identity.core.use_cases import VerifyPendingConfirmationContextUseCase
from shifu.fakers.identity.entities import AccountFaker


CONFIRMATION_HASH = 'confirmation-secret-hash'


class TestVerifyPendingConfirmationContextUseCase:
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
        self.pending_handle_provider = create_autospec(
            ActionTokenProvider,
            instance=True,
        )
        self.subject = VerifyPendingConfirmationContextUseCase(
            identity_database=self.database,
            pending_confirmation_handle_provider=self.pending_handle_provider,
        )

    def test_should_accept_a_used_confirmation_handle_for_the_activated_account(
        self,
    ) -> None:
        now = datetime(2026, 9, 23, tzinfo=UTC)
        account = AccountFaker.fake(status=AccountStatus.ACTIVE)
        token = AccountActionToken(
            id='01SHIFUVERIFYPENDING000001',
            account_id=account.id,
            type=AccountActionTokenType.EMAIL_CONFIRMATION,
            status=AccountActionTokenStatus.USED,
            token_hash=CONFIRMATION_HASH,
            issued_at=now,
            expires_at=now,
            updated_at=now,
            used_at=now,
            communication_id='01SHIFUVERIFYPENDING000002',
            pending_handle_hash='pending-handle-hash',
        )
        self.pending_handle_provider.hash.return_value = 'pending-handle-hash'
        self.token_repository.find_by_pending_handle_hash.return_value = token
        self.repositories.accounts.find_by_id.return_value = account

        result = self.subject.execute('A' * 43, account.id)

        assert result is True

    def test_should_reject_a_pending_handle_for_another_account(self) -> None:
        now = datetime(2026, 9, 23, tzinfo=UTC)
        account = AccountFaker.fake(status=AccountStatus.ACTIVE)
        token = AccountActionToken(
            id='01SHIFUVERIFYPENDING000003',
            account_id='01SHIFUOTHERACCOUNT0000001',
            type=AccountActionTokenType.EMAIL_CONFIRMATION,
            status=AccountActionTokenStatus.USED,
            token_hash=CONFIRMATION_HASH,
            issued_at=now,
            expires_at=now,
            updated_at=now,
            used_at=now,
            communication_id='01SHIFUVERIFYPENDING000004',
            pending_handle_hash='pending-handle-hash',
        )
        self.pending_handle_provider.hash.return_value = 'pending-handle-hash'
        self.token_repository.find_by_pending_handle_hash.return_value = token
        self.repositories.accounts.find_by_id.return_value = account

        result = self.subject.execute('A' * 43, account.id)

        assert result is False
