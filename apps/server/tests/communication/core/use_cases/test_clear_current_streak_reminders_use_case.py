from datetime import UTC, datetime, timedelta
from unittest.mock import call, create_autospec

import pytest

from shifu.communication.core.domain.entities import StreakReminder
from shifu.communication.core.domain.enums import StreakReminderStatus
from shifu.communication.core.interfaces import (
    CommunicationDatabase,
    CommunicationDatabaseRepositories,
)
from shifu.communication.core.use_cases import ClearCurrentStreakRemindersUseCase
from shifu.fakers.communication.entities import StreakReminderFaker
from shifu.shared.core.interfaces import ClockProvider


class TestClearCurrentStreakRemindersUseCase:
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
        self.clock_provider = create_autospec(ClockProvider, instance=True)
        self.now = datetime(2026, 11, 19, 0, 20, tzinfo=UTC)
        self.clock_provider.now.return_value = self.now
        self.subject = ClearCurrentStreakRemindersUseCase(
            self.database,
            self.clock_provider,
        )

    def _reminder(self, status: StreakReminderStatus) -> StreakReminder:
        return StreakReminderFaker.fake(
            account_id=self.ACCOUNT_ID,
            status=status,
            expires_at=self.now + timedelta(hours=3),
        )

    @pytest.mark.parametrize('status', list(StreakReminderStatus))
    def test_should_remove_the_open_reminder_whatever_its_status(
        self, status: StreakReminderStatus
    ) -> None:
        reminder = self._reminder(status)
        self.repositories.streak_reminders.find_many_open_by_account_id.return_value = (
            reminder,
        )

        cleared = self.subject.execute(self.ACCOUNT_ID)

        assert cleared == 1
        self.repositories.streak_reminders.find_many_open_by_account_id.assert_called_once_with(
            self.ACCOUNT_ID,
            now=self.now,
        )
        self.repositories.streak_reminders.remove.assert_called_once_with(reminder)

    def test_should_remove_every_open_reminder_of_the_account(self) -> None:
        sent = self._reminder(StreakReminderStatus.SENT)
        skipped = self._reminder(StreakReminderStatus.SKIPPED)
        self.repositories.streak_reminders.find_many_open_by_account_id.return_value = (
            sent,
            skipped,
        )

        cleared = self.subject.execute(self.ACCOUNT_ID)

        assert cleared == 2
        assert self.repositories.streak_reminders.remove.call_args_list == [
            call(sent),
            call(skipped),
        ]

    def test_should_be_a_no_op_when_the_account_has_no_open_reminder(self) -> None:
        self.repositories.streak_reminders.find_many_open_by_account_id.return_value = ()

        assert self.subject.execute(self.ACCOUNT_ID) == 0
        assert self.subject.execute(self.ACCOUNT_ID) == 0

        self.repositories.streak_reminders.remove.assert_not_called()

    def test_should_not_touch_subscriptions_preferences_or_events(self) -> None:
        self.repositories.streak_reminders.find_many_open_by_account_id.return_value = (
            self._reminder(StreakReminderStatus.SENT),
        )

        self.subject.execute(self.ACCOUNT_ID)

        self.repositories.push_subscriptions.remove.assert_not_called()
        self.repositories.push_subscriptions.remove_many_by_account_id.assert_not_called()
        self.repositories.streak_reminder_preferences.remove_by_account_id.assert_not_called()
        self.repositories.events.add.assert_not_called()
