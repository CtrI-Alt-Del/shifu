from datetime import UTC, date, datetime
from unittest.mock import create_autospec

import pytest

from shifu.communication.core.domain.enums import StreakReminderStatus
from shifu.communication.core.domain.entities import StreakReminderPreference
from shifu.communication.core.domain.structures import StreakReminderRequest
from shifu.communication.core.interfaces import (
    CommunicationDatabase,
    CommunicationDatabaseRepositories,
)
from shifu.communication.core.use_cases import QueueStreakReminderUseCase
from shifu.fakers.communication.entities import (
    PushSubscriptionFaker,
    StreakReminderFaker,
)
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class TestQueueStreakReminderUseCase:
    ACCOUNT_ID = '01JACCOUNT000000000000000001'
    REMINDER_ID = '01JREMINDER0000000000000001'

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
        self.id_provider = create_autospec(IdentifierProvider, instance=True)
        self.id_provider.generate.return_value = self.REMINDER_ID
        self.clock_provider = create_autospec(ClockProvider, instance=True)
        self.now = datetime(2026, 11, 18, 21, 0, tzinfo=UTC)
        self.clock_provider.now.return_value = self.now
        self.request = StreakReminderRequest(
            account_id=self.ACCOUNT_ID,
            local_date=date(2026, 11, 18),
            streak_days=7,
            expires_at=datetime(2026, 11, 19, 3, 0, tzinfo=UTC),
        )
        self.repositories.streak_reminders.try_add.return_value = True
        self.repositories.streak_reminder_preferences.find_by_account_id.return_value = StreakReminderPreference.create(
            account_id=self.ACCOUNT_ID,
            enabled=True,
            now=self.now,
        )
        self.repositories.push_subscriptions.find_many_by_account_id.return_value = (
            PushSubscriptionFaker.fake(account_id=self.ACCOUNT_ID),
        )
        self.subject = QueueStreakReminderUseCase(
            self.database,
            self.id_provider,
            self.clock_provider,
        )

    def test_should_record_a_pending_reminder_when_it_can_be_delivered(self) -> None:
        result = self.subject.execute(self.request)

        assert result.id == self.REMINDER_ID
        assert result.account_id == self.ACCOUNT_ID
        assert result.local_date == date(2026, 11, 18)
        assert result.streak_days == 7
        assert result.status is StreakReminderStatus.PENDING
        assert result.expires_at == self.request.expires_at
        assert result.attempt_count == 0
        assert result.next_attempt_at is None
        assert result.completed_at is None
        self.repositories.streak_reminders.try_add.assert_called_once_with(result)
        self.repositories.streak_reminders.update.assert_not_called()

    def test_should_skip_immediately_when_the_preference_is_off(self) -> None:
        self.repositories.streak_reminder_preferences.find_by_account_id.return_value = StreakReminderPreference.create(
            account_id=self.ACCOUNT_ID,
            enabled=False,
            now=self.now,
        )

        result = self.subject.execute(self.request)

        assert result.status is StreakReminderStatus.SKIPPED
        assert result.completed_at == self.now
        self.repositories.streak_reminders.update.assert_called_once_with(result)

    def test_should_skip_immediately_when_the_preference_was_never_set(self) -> None:
        self.repositories.streak_reminder_preferences.find_by_account_id.return_value = None

        result = self.subject.execute(self.request)

        assert result.status is StreakReminderStatus.SKIPPED
        self.repositories.streak_reminders.update.assert_called_once_with(result)

    def test_should_skip_immediately_when_the_account_has_no_subscription(self) -> None:
        self.repositories.push_subscriptions.find_many_by_account_id.return_value = ()

        result = self.subject.execute(self.request)

        assert result.status is StreakReminderStatus.SKIPPED
        assert result.completed_at == self.now
        self.repositories.streak_reminders.update.assert_called_once_with(result)

    def test_should_return_the_existing_reminder_on_a_replay(self) -> None:
        existing = StreakReminderFaker.fake(
            account_id=self.ACCOUNT_ID,
            local_date=self.request.local_date,
            status=StreakReminderStatus.SENT,
        )
        self.repositories.streak_reminders.try_add.return_value = False
        self.repositories.streak_reminders.find_by_account_id_and_local_date.return_value = existing

        result = self.subject.execute(self.request)

        assert result is existing
        self.repositories.streak_reminders.find_by_account_id_and_local_date.assert_called_once_with(
            self.ACCOUNT_ID,
            self.request.local_date,
        )
        self.repositories.streak_reminders.update.assert_not_called()
        self.repositories.streak_reminder_preferences.find_by_account_id.assert_not_called()
        self.repositories.push_subscriptions.find_many_by_account_id.assert_not_called()
