from datetime import UTC, datetime
from unittest.mock import Mock, call, create_autospec

import pytest

from shifu.communication.core.domain.enums import StreakReminderStatus
from shifu.communication.core.interfaces import (
    CommunicationDatabase,
    CommunicationDatabaseRepositories,
)
from shifu.communication.core.use_cases import DeleteAccountPushDataUseCase
from shifu.fakers.communication.entities import StreakReminderFaker
from shifu.shared.core.interfaces import ClockProvider


class TestDeleteAccountPushDataUseCase:
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
        self.now = datetime(2026, 11, 18, 21, 0, tzinfo=UTC)
        self.clock_provider.now.return_value = self.now
        self.subject = DeleteAccountPushDataUseCase(self.database, self.clock_provider)

    def test_should_cancel_pending_reminders_before_removing_the_account_data(
        self,
    ) -> None:
        pending = StreakReminderFaker.fake(
            account_id=self.ACCOUNT_ID,
            attempt_count=1,
            next_attempt_at=datetime(2026, 11, 18, 21, 5, tzinfo=UTC),
        )
        other_pending = StreakReminderFaker.fake(account_id=self.ACCOUNT_ID)
        self.repositories.streak_reminders.find_many_pending_by_account_id.return_value = (
            pending,
            other_pending,
        )
        manager = Mock()
        manager.attach_mock(self.repositories.streak_reminders.update, 'update')
        manager.attach_mock(
            self.repositories.streak_reminders.remove_many_by_account_id,
            'remove_many',
        )

        self.subject.execute(self.ACCOUNT_ID)

        assert pending.status is StreakReminderStatus.CANCELLED
        assert pending.next_attempt_at is None
        assert pending.completed_at == self.now
        assert other_pending.status is StreakReminderStatus.CANCELLED
        assert manager.mock_calls == [
            call.update(pending),
            call.update(other_pending),
            call.remove_many(self.ACCOUNT_ID),
        ]
        self.repositories.streak_reminders.find_many_pending_by_account_id.assert_called_once_with(
            self.ACCOUNT_ID
        )
        self.repositories.push_subscriptions.remove_many_by_account_id.assert_called_once_with(
            self.ACCOUNT_ID
        )
        self.repositories.streak_reminder_preferences.remove_by_account_id.assert_called_once_with(
            self.ACCOUNT_ID
        )

    def test_should_be_a_no_op_when_the_account_has_no_data(self) -> None:
        self.repositories.streak_reminders.find_many_pending_by_account_id.return_value = ()

        self.subject.execute(self.ACCOUNT_ID)
        self.subject.execute(self.ACCOUNT_ID)

        self.repositories.streak_reminders.update.assert_not_called()
        assert (
            self.repositories.streak_reminders.remove_many_by_account_id.call_args_list
            == [call(self.ACCOUNT_ID), call(self.ACCOUNT_ID)]
        )

    def test_should_not_touch_deliveries_or_other_aggregates_directly(self) -> None:
        self.repositories.streak_reminders.find_many_pending_by_account_id.return_value = ()

        self.subject.execute(self.ACCOUNT_ID)

        self.repositories.push_deliveries.remove.assert_not_called()
        self.repositories.communications.remove_all.assert_not_called()
        self.repositories.events.add.assert_not_called()
