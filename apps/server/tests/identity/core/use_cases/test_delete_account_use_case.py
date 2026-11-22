from datetime import UTC, datetime
from unittest.mock import create_autospec
from uuid import uuid4

import pytest

from shifu.fakers.identity.entities import AccountFaker
from shifu.identity.core.domain.enums import AccountStatus
from shifu.identity.core.domain.errors import (
    AccountDeletionNotAllowedError,
    InvalidCurrentPasswordError,
)
from shifu.identity.core.domain.events import AccountErasureRequestedEvent
from shifu.identity.core.domain.structures import (
    AccountErasureResult,
    DeleteAccountInput,
)
from shifu.identity.core.interfaces import (
    IdentityDatabase,
    IdentityDatabaseRepositories,
    PasswordHashingProvider,
)
from shifu.identity.core.use_cases import DeleteAccountUseCase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider


class TestDeleteAccountUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(IdentityDatabase, instance=True)
        self.repositories = create_autospec(IdentityDatabaseRepositories, instance=True)
        self.database.account_closure_transaction.return_value.__enter__.return_value = self.repositories
        self.now = datetime(2026, 11, 21, tzinfo=UTC)
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = self.now
        self.account = AccountFaker.fake(access_version=4)
        self.user = AuthenticatedUser(
            account_id=self.account.id,
            display_name=self.account.display_name,
            time_zone=self.account.time_zone,
            session_id='session-a',
            token_access_version=4,
            account_access_version=4,
        )
        self.repositories.accounts.find_by_id.return_value = self.account
        self.repositories.account_erasures.find_result.return_value = None
        self.repositories.external_effect_receipts.has_unresolved_for_account_id.return_value = False
        self.hasher = create_autospec(PasswordHashingProvider, instance=True)
        self.hasher.verify.return_value = True
        self.subject = DeleteAccountUseCase(self.database, self.clock, self.hasher)
        self.erasure_id = uuid4()
        self.current_password = 'current-password'
        self.request = DeleteAccountInput(
            account_id=self.account.id,
            erasure_id=self.erasure_id,
            current_password=self.current_password,
            confirmed=True,
        )

    def test_should_close_and_remove_settled_external_effect_receipts(self) -> None:
        password_hash = self.account.password_hash
        result = self.subject.execute(self.user, self.request)

        assert result.state == 'closed'
        assert result.closed_at == self.now
        assert result.erasure == 'pending'
        assert self.account.status is AccountStatus.DELETED
        assert self.account.access_version == 5
        assert self.account.display_name == 'Conta encerrada'
        assert self.account.email.endswith('@invalid.local')
        assert self.account.password_hash == '!disabled!'
        self.hasher.verify.assert_called_once_with(self.current_password, password_hash)
        self.repositories.accounts.update.assert_called_once_with(self.account)
        self.repositories.external_effect_receipts.has_unresolved_for_account_id.assert_called_once_with(
            self.account.id
        )
        self.repositories.external_effect_receipts.remove_settled_for_account_id.assert_called_once_with(
            self.account.id
        )
        self.repositories.account_action_tokens.remove_by_account_id.assert_called_once_with(
            self.account.id
        )
        self.repositories.account_browser_capabilities.revoke_by_account_id.assert_called_once_with(
            self.account.id
        )
        self.repositories.account_erasures.add.assert_called_once()
        self.repositories.events.remove_by_account_id_and_names.assert_called_once()
        event = self.repositories.events.add.call_args.args[0]
        assert isinstance(event, AccountErasureRequestedEvent)
        assert event.payload.erasure_id == str(self.erasure_id)

    def test_should_preserve_the_account_when_an_external_effect_is_unresolved(
        self,
    ) -> None:
        account_before = (
            self.account.status,
            self.account.access_version,
            self.account.email,
            self.account.display_name,
            self.account.password_hash,
        )
        self.repositories.external_effect_receipts.has_unresolved_for_account_id.return_value = True

        with pytest.raises(AccountDeletionNotAllowedError):
            self.subject.execute(self.user, self.request)

        assert (
            self.account.status,
            self.account.access_version,
            self.account.email,
            self.account.display_name,
            self.account.password_hash,
        ) == account_before
        self.repositories.external_effect_receipts.has_unresolved_for_account_id.assert_called_once_with(
            self.account.id
        )
        self.repositories.external_effect_receipts.remove_settled_for_account_id.assert_not_called()
        self.repositories.accounts.update.assert_not_called()
        self.repositories.account_action_tokens.remove_by_account_id.assert_not_called()
        self.repositories.account_browser_capabilities.revoke_by_account_id.assert_not_called()
        self.repositories.account_erasures.add.assert_not_called()
        self.repositories.events.add.assert_not_called()
        self.repositories.events.remove_by_account_id_and_names.assert_not_called()

    def test_should_reject_when_confirmation_is_missing(self) -> None:
        request = DeleteAccountInput(
            account_id=self.account.id,
            erasure_id=self.erasure_id,
            current_password=self.current_password,
            confirmed=False,
        )

        with pytest.raises(AccountDeletionNotAllowedError):
            self.subject.execute(self.user, request)

        self.database.account_closure_transaction.assert_not_called()
        self.hasher.verify.assert_not_called()

    def test_should_reject_wrong_password_without_closing(self) -> None:
        self.hasher.verify.return_value = False

        with pytest.raises(InvalidCurrentPasswordError):
            self.subject.execute(self.user, self.request)

        assert self.account.status is AccountStatus.ACTIVE
        self.repositories.accounts.update.assert_not_called()
        self.repositories.account_erasures.add.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_reject_a_stale_access_version(self) -> None:
        self.account.access_version = 5

        with pytest.raises(AuthorizationError):
            self.subject.execute(self.user, self.request)

        self.hasher.verify.assert_not_called()
        self.repositories.accounts.update.assert_not_called()

    def test_should_return_the_existing_pending_erasure_for_same_actor(self) -> None:
        existing = AccountErasureResult(
            state='closed', closed_at=self.now, erasure='pending'
        )
        self.repositories.account_erasures.find_result.return_value = existing
        self.repositories.account_erasures.find_account_id.return_value = (
            self.account.id
        )

        result = self.subject.execute(self.user, self.request)

        assert result is existing
        self.repositories.accounts.find_by_id.assert_not_called()
        self.repositories.events.add.assert_not_called()
