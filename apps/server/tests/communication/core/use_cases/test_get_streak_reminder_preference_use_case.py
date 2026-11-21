from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.communication.core.domain.entities import StreakReminderPreference
from shifu.communication.core.interfaces import (
    CommunicationDatabase,
    CommunicationDatabaseRepositories,
)
from shifu.communication.core.use_cases import GetStreakReminderPreferenceUseCase


class TestGetStreakReminderPreferenceUseCase:
    ACCOUNT_ID = '01JACCOUNT000000000000000001'

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(CommunicationDatabase, instance=True)
        self.repositories = create_autospec(
            CommunicationDatabaseRepositories,
            instance=True,
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.subject = GetStreakReminderPreferenceUseCase(self.database)

    def test_should_default_to_off_when_the_account_never_changed_it(self) -> None:
        self.repositories.streak_reminder_preferences.find_by_account_id.return_value = None

        assert self.subject.execute(self.ACCOUNT_ID) is False
        self.repositories.streak_reminder_preferences.find_by_account_id.assert_called_once_with(
            self.ACCOUNT_ID
        )

    @pytest.mark.parametrize('enabled', [True, False])
    def test_should_return_the_stored_preference(self, enabled: bool) -> None:
        self.repositories.streak_reminder_preferences.find_by_account_id.return_value = StreakReminderPreference.create(
            account_id=self.ACCOUNT_ID,
            enabled=enabled,
            now=datetime(2026, 11, 18, tzinfo=UTC),
        )

        assert self.subject.execute(self.ACCOUNT_ID) is enabled
