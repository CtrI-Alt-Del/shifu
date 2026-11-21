from datetime import UTC, date, datetime
from unittest.mock import create_autospec

import pytest

from shifu.fakers.gamification.entities import GamificationProfileFaker
from shifu.gamification.core.domain.enums import StreakReminderInviteStatus
from shifu.gamification.core.domain.errors import GamificationProfileNotFoundError
from shifu.gamification.core.domain.structures import (
    PracticeStreak,
    StreakReminderSettings,
)
from shifu.gamification.core.interfaces import (
    GamificationDatabase,
    GamificationDatabaseRepositories,
)
from shifu.gamification.core.use_cases import GetStreakReminderSettingsUseCase

ACCOUNT_ID = 'account-1'
ANSWERED_AT = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)
PRACTICED = PracticeStreak(current=1, longest=1, latest_practice_date=date(2026, 9, 14))


class TestGetStreakReminderSettingsUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(GamificationDatabase, instance=True)
        self.repositories = create_autospec(
            GamificationDatabaseRepositories, instance=True
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.subject = GetStreakReminderSettingsUseCase(self.database)

    def _given_profile(
        self,
        *,
        streak: PracticeStreak | None = None,
        reminder_hour: int = 18,
        answered_at: datetime | None = None,
    ) -> None:
        self.repositories.profiles.find_by_account_id.return_value = (
            GamificationProfileFaker.fake(
                account_id=ACCOUNT_ID,
                streak=streak,
                reminder_hour=reminder_hour,
                reminder_invite_answered_at=answered_at,
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )

    def test_should_default_to_hour_18_and_not_eligible_before_any_practice_day(
        self,
    ) -> None:
        self._given_profile()

        settings = self.subject.execute(ACCOUNT_ID)

        assert settings == StreakReminderSettings(
            hour=18, invite_status=StreakReminderInviteStatus.NOT_ELIGIBLE
        )
        self.repositories.profiles.find_by_account_id.assert_called_once_with(
            ACCOUNT_ID
        )

    def test_should_report_the_invite_as_pending_after_the_first_practice_day(
        self,
    ) -> None:
        self._given_profile(streak=PRACTICED)

        settings = self.subject.execute(ACCOUNT_ID)

        assert settings.invite_status is StreakReminderInviteStatus.PENDING

    def test_should_report_the_invite_as_pending_when_the_streak_was_broken(
        self,
    ) -> None:
        self._given_profile(
            streak=PracticeStreak(
                current=0, longest=3, latest_practice_date=date(2026, 9, 1)
            )
        )

        settings = self.subject.execute(ACCOUNT_ID)

        assert settings.invite_status is StreakReminderInviteStatus.PENDING

    def test_should_report_the_invite_as_answered_once_it_was_answered(self) -> None:
        self._given_profile(streak=PRACTICED, answered_at=ANSWERED_AT)

        settings = self.subject.execute(ACCOUNT_ID)

        assert settings.invite_status is StreakReminderInviteStatus.ANSWERED

    def test_should_return_the_stored_hour(self) -> None:
        self._given_profile(streak=PRACTICED, reminder_hour=7)

        settings = self.subject.execute(ACCOUNT_ID)

        assert settings.hour == 7

    def test_should_not_write_anything_when_reading(self) -> None:
        self._given_profile(streak=PRACTICED)

        self.subject.execute(ACCOUNT_ID)

        self.repositories.profiles.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_fail_when_the_account_has_no_profile(self) -> None:
        self.repositories.profiles.find_by_account_id.return_value = None

        with pytest.raises(GamificationProfileNotFoundError):
            self.subject.execute(ACCOUNT_ID)
