from datetime import UTC, date, datetime
from unittest.mock import create_autospec

import pytest

from shifu.fakers.gamification.entities import GamificationProfileFaker
from shifu.gamification.core.domain.entities import GamificationProfile
from shifu.gamification.core.domain.enums import StreakReminderInviteStatus
from shifu.gamification.core.domain.errors import (
    GamificationProfileNotFoundError,
    InvalidStreakReminderHourError,
)
from shifu.gamification.core.domain.structures import PracticeStreak
from shifu.gamification.core.interfaces import (
    GamificationDatabase,
    GamificationDatabaseRepositories,
)
from shifu.gamification.core.use_cases import ChangeStreakReminderHourUseCase

ACCOUNT_ID = 'account-1'
CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)
NOW = datetime(2026, 9, 15, 18, 50, tzinfo=UTC)
ANSWERED_AT = datetime(2026, 9, 10, tzinfo=UTC)


class TestChangeStreakReminderHourUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(GamificationDatabase, instance=True)
        self.repositories = create_autospec(
            GamificationDatabaseRepositories, instance=True
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.profile = GamificationProfileFaker.fake(
            account_id=ACCOUNT_ID,
            total_xp=120,
            streak=PracticeStreak(
                current=2, longest=4, latest_practice_date=date(2026, 9, 14)
            ),
            reminder_hour=20,
            reminder_invite_answered_at=ANSWERED_AT,
            created_at=CREATED_AT,
        )
        self.repositories.profiles.find_by_account_id_for_update.return_value = (
            self.profile
        )
        self.subject = ChangeStreakReminderHourUseCase(self.database)

    @pytest.mark.parametrize('hour', [6, 7, 18, 19, 22])
    def test_should_store_every_whole_hour_from_6_to_22(self, hour: int) -> None:
        settings = self.subject.execute(ACCOUNT_ID, hour, now=NOW)

        assert settings.hour == hour
        self.repositories.profiles.update.assert_called_once_with(self.profile)
        assert self.profile.reminder_hour == hour
        assert self.profile.updated_at == NOW

    def test_should_default_a_new_profile_to_hour_18(self) -> None:
        assert GamificationProfileFaker.fake().reminder_hour == 18
        assert GamificationProfile.DEFAULT_REMINDER_HOUR == 18
        assert GamificationProfile.REMINDER_HOUR_MIN == 6
        assert GamificationProfile.REMINDER_HOUR_MAX == 22

    @pytest.mark.parametrize('hour', [5, 23, 0, 24, -1, 99])
    def test_should_reject_an_hour_outside_6_to_22_without_updating(
        self, hour: int
    ) -> None:
        with pytest.raises(InvalidStreakReminderHourError):
            self.subject.execute(ACCOUNT_ID, hour, now=NOW)

        self.repositories.profiles.update.assert_not_called()
        self.repositories.events.add.assert_not_called()
        assert self.profile.reminder_hour == 20
        assert self.profile.updated_at == CREATED_AT

    def test_should_reject_a_boolean_as_an_hour(self) -> None:
        with pytest.raises(InvalidStreakReminderHourError):
            self.subject.execute(ACCOUNT_ID, True, now=NOW)  # noqa: FBT003

        self.repositories.profiles.update.assert_not_called()

    def test_should_return_the_settings_with_the_current_invite_status(self) -> None:
        settings = self.subject.execute(ACCOUNT_ID, 19, now=NOW)

        assert settings.invite_status is StreakReminderInviteStatus.ANSWERED

    def test_should_change_only_the_hour_and_the_update_instant(self) -> None:
        self.subject.execute(ACCOUNT_ID, 19, now=NOW)

        assert self.profile.total_xp == 120
        assert self.profile.streak == PracticeStreak(
            current=2, longest=4, latest_practice_date=date(2026, 9, 14)
        )
        assert self.profile.reminder_invite_answered_at == ANSWERED_AT

        # Writers lock the row, so they must not use the plain read.
        self.repositories.profiles.find_by_account_id_for_update.assert_called_with(
            ACCOUNT_ID
        )
        self.repositories.profiles.find_by_account_id.assert_not_called()

    def test_should_fail_when_the_account_has_no_profile(self) -> None:
        self.repositories.profiles.find_by_account_id_for_update.return_value = None

        with pytest.raises(GamificationProfileNotFoundError):
            self.subject.execute(ACCOUNT_ID, 19, now=NOW)

        self.repositories.profiles.update.assert_not_called()
