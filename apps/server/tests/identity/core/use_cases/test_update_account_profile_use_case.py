from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.fakers.identity.entities import AccountFaker
from shifu.identity.core.interfaces import (
    IdentityDatabase,
    IdentityDatabaseRepositories,
)
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider
from shifu.identity.core.domain.errors import (
    InvalidDisplayNameError,
    InvalidTimeZoneError,
)
from shifu.identity.core.domain.structures import AccountProfileUpdate
from shifu.identity.core.use_cases import UpdateAccountProfileUseCase


class TestUpdateAccountProfileUseCase:
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
        self.subject = UpdateAccountProfileUseCase(self.database, self.clock)

    @pytest.mark.parametrize('name', ['a', 'á' * 160, 'Same name'])
    def test_should_normalize_name_and_preserve_identity_credentials_and_access(
        self, name: str
    ) -> None:
        self.account.retained_session_id = 'older-session'
        self.account.retained_session_access_version = 3
        original = (
            self.account.id,
            self.account.email,
            self.account.password_hash,
            self.account.created_at,
        )
        result = self.subject.execute(
            self.user,
            AccountProfileUpdate(display_name='  ' + name + '  ', time_zone='UTC'),
        )
        assert result.display_name == name
        assert result.time_zone == 'UTC'
        assert (
            self.account.id,
            self.account.email,
            self.account.password_hash,
            self.account.created_at,
        ) == original
        assert self.account.access_version == 4
        assert self.account.retained_session_id == 'older-session'
        assert self.account.retained_session_access_version == 3
        assert self.account.updated_at == self.now
        self.repositories.accounts.update.assert_called_once_with(self.account)
        self.repositories.events.add.assert_not_called()

    @pytest.mark.parametrize('name', ['', '   ', 'a' * 161])
    def test_should_reject_invalid_names_without_effects(self, name: str) -> None:
        with pytest.raises(InvalidDisplayNameError):
            self.subject.execute(
                self.user, AccountProfileUpdate(display_name=name, time_zone='UTC')
            )
        self.database.transaction.assert_not_called()

    @pytest.mark.parametrize(
        'zone', ['', 'GMT+03:00', '/etc/passwd', '../UTC', 'a' * 65, 'Unknown/Zone']
    )
    def test_should_reject_invalid_zone_without_effects(self, zone: str) -> None:
        with pytest.raises(InvalidTimeZoneError):
            self.subject.execute(
                self.user, AccountProfileUpdate(display_name='Name', time_zone=zone)
            )
        self.database.transaction.assert_not_called()

    def test_should_revalidate_snapshot_before_writing(self) -> None:
        self.account.access_version = 5
        with pytest.raises(AuthorizationError):
            self.subject.execute(
                self.user, AccountProfileUpdate(display_name='New', time_zone='UTC')
            )
        self.repositories.accounts.update.assert_not_called()

    @pytest.mark.parametrize(
        'zone', ['UTC', 'America/Sao_Paulo', 'Europe/Lisbon', 'Asia/Kathmandu']
    )
    def test_should_accept_supported_iana_zones(self, zone: str) -> None:
        profile = self.subject.execute(
            self.user, AccountProfileUpdate(display_name='Same name', time_zone=zone)
        )
        assert profile.time_zone == zone
        self.repositories.accounts.find_by_id.assert_called_once_with(
            self.user.account_id
        )
        self.repositories.accounts.find_non_deleted_by_email.assert_not_called()
