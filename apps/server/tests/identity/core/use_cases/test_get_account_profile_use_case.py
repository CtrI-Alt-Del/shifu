from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.fakers.identity.entities import AccountFaker
from shifu.identity.core.domain.enums import AccountStatus
from shifu.identity.core.interfaces import (
    IdentityDatabase,
    IdentityDatabaseRepositories,
)
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider
from shifu.identity.core.use_cases import GetAccountProfileUseCase


class TestGetAccountProfileUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(IdentityDatabase, instance=True)
        self.repositories = create_autospec(IdentityDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.now = datetime(2026, 10, 25, tzinfo=UTC)
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
        self.subject = GetAccountProfileUseCase(self.database)

    def test_should_return_canonical_profile_without_writes(self) -> None:
        self.account.time_zone = None
        result = self.subject.execute(self.user)
        assert result.account_id == self.account.id
        assert result.email == self.account.email
        assert result.display_name == self.account.display_name
        assert result.time_zone is None
        self.repositories.accounts.update.assert_not_called()

    @pytest.mark.parametrize(
        'status', [AccountStatus.PENDING_CONFIRMATION, AccountStatus.DELETED]
    )
    def test_should_reject_inactive_accounts(self, status: AccountStatus) -> None:
        self.account.status = status
        with pytest.raises(AuthorizationError):
            self.subject.execute(self.user)
        self.repositories.accounts.update.assert_not_called()

    @pytest.mark.parametrize(
        'context', ['missing', 'stale', 'wrong-session', 'wrong-version']
    )
    def test_should_reject_missing_or_revoked_context(self, context: str) -> None:
        self.account.access_version = 5
        self.account.retained_session_id = 'session-a'
        self.account.retained_session_access_version = 4
        user = AuthenticatedUser(
            account_id=self.account.id,
            display_name='Name',
            time_zone=None,
            session_id=None
            if context == 'missing'
            else 'session-b'
            if context == 'wrong-session'
            else 'session-a',
            token_access_version=3 if context == 'wrong-version' else 4,
            account_access_version=4 if context == 'stale' else 5,
        )
        with pytest.raises(AuthorizationError):
            self.subject.execute(user)

    def test_should_accept_exact_retained_pair_and_reject_missing_account(self) -> None:
        self.account.retained_session_id = 'session-a'
        self.account.retained_session_access_version = 3
        user = AuthenticatedUser(
            account_id=self.account.id,
            display_name='Name',
            time_zone=None,
            session_id='session-a',
            token_access_version=3,
            account_access_version=4,
        )
        assert self.subject.execute(user).account_id == self.account.id
        self.repositories.accounts.find_by_id.return_value = None
        with pytest.raises(AuthorizationError):
            self.subject.execute(user)
