from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.communication.core.domain.entities import StreakReminderPreference
from shifu.communication.core.interfaces import (
    CommunicationDatabase,
    CommunicationDatabaseRepositories,
)
from shifu.communication.core.use_cases import ChangeStreakReminderPreferenceUseCase


class TestChangeStreakReminderPreferenceUseCase:
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
        self.now = datetime(2026, 11, 18, 21, 0, tzinfo=UTC)
        self.repositories.streak_reminder_preferences.try_add.return_value = True
        self.subject = ChangeStreakReminderPreferenceUseCase(self.database)

    def test_should_create_the_preference_on_the_first_change(self) -> None:
        self.repositories.streak_reminder_preferences.find_by_account_id.return_value = None

        result = self.subject.execute(self.ACCOUNT_ID, enabled=True, now=self.now)

        assert result is True
        added = self.repositories.streak_reminder_preferences.try_add.call_args.args[0]
        assert isinstance(added, StreakReminderPreference)
        assert added.id == self.ACCOUNT_ID
        assert added.enabled is True
        assert added.updated_at == self.now
        self.repositories.streak_reminder_preferences.update.assert_not_called()

    @pytest.mark.parametrize('enabled', [True, False])
    def test_should_update_an_existing_preference(self, enabled: bool) -> None:
        existing = StreakReminderPreference.create(
            account_id=self.ACCOUNT_ID,
            enabled=not enabled,
            now=datetime(2026, 11, 1, tzinfo=UTC),
        )
        self.repositories.streak_reminder_preferences.find_by_account_id.return_value = existing

        result = self.subject.execute(self.ACCOUNT_ID, enabled=enabled, now=self.now)

        assert result is enabled
        assert existing.enabled is enabled
        assert existing.updated_at == self.now
        self.repositories.streak_reminder_preferences.update.assert_called_once_with(
            existing
        )
        self.repositories.streak_reminder_preferences.try_add.assert_not_called()

    def test_should_only_touch_the_callers_preference(self) -> None:
        self.repositories.streak_reminder_preferences.find_by_account_id.return_value = None

        self.subject.execute(self.ACCOUNT_ID, enabled=False, now=self.now)

        self.repositories.streak_reminder_preferences.find_by_account_id.assert_called_once_with(
            self.ACCOUNT_ID
        )

    @pytest.mark.parametrize('enabled', [True, False])
    def test_should_apply_the_change_on_top_of_a_concurrent_first_change(
        self, enabled: bool
    ) -> None:
        winner = StreakReminderPreference.create(
            account_id=self.ACCOUNT_ID,
            enabled=not enabled,
            now=datetime(2026, 11, 17, tzinfo=UTC),
        )
        self.repositories.streak_reminder_preferences.find_by_account_id.side_effect = [
            None,
            winner,
        ]
        self.repositories.streak_reminder_preferences.try_add.return_value = False

        result = self.subject.execute(self.ACCOUNT_ID, enabled=enabled, now=self.now)

        assert result is enabled
        assert winner.enabled is enabled
        assert winner.updated_at == self.now
        self.repositories.streak_reminder_preferences.update.assert_called_once_with(
            winner
        )
