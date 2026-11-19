from datetime import UTC, date, datetime
from unittest.mock import create_autospec

import pytest

from shifu.fakers.gamification.entities import GamificationProfileFaker
from shifu.gamification.core.domain.enums import StreakReminderInviteStatus
from shifu.gamification.core.domain.errors import GamificationProfileNotFoundError
from shifu.gamification.core.domain.structures import PracticeStreak
from shifu.gamification.core.interfaces import (
    GamificationDatabase,
    GamificationDatabaseRepositories,
)
from shifu.gamification.core.use_cases import AnswerStreakReminderInviteUseCase

ACCOUNT_ID = 'account-1'
CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)
FIRST_ANSWER = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)
LATER_ANSWER = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


class TestAnswerStreakReminderInviteUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(GamificationDatabase, instance=True)
        self.repositories = create_autospec(
            GamificationDatabaseRepositories, instance=True
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.subject = AnswerStreakReminderInviteUseCase(self.database)

    def _given_profile(self, *, answered_at: datetime | None = None) -> None:
        self.profile = GamificationProfileFaker.fake(
            account_id=ACCOUNT_ID,
            streak=PracticeStreak(
                current=1, longest=1, latest_practice_date=date(2026, 9, 14)
            ),
            reminder_hour=19,
            reminder_invite_answered_at=answered_at,
            created_at=CREATED_AT,
        )
        self.repositories.profiles.find_by_account_id_for_update.return_value = (
            self.profile
        )

    def test_should_record_the_first_answer_and_report_it_as_answered(self) -> None:
        self._given_profile()

        settings = self.subject.execute(ACCOUNT_ID, now=FIRST_ANSWER)

        assert settings.invite_status is StreakReminderInviteStatus.ANSWERED
        assert settings.hour == 19
        assert self.profile.reminder_invite_answered_at == FIRST_ANSWER
        self.repositories.profiles.update.assert_called_once_with(self.profile)

        # Writers lock the row, so they must not use the plain read.
        self.repositories.profiles.find_by_account_id_for_update.assert_called_with(
            ACCOUNT_ID
        )
        self.repositories.profiles.find_by_account_id.assert_not_called()

    def test_should_keep_the_first_answer_when_answered_again(self) -> None:
        self._given_profile(answered_at=FIRST_ANSWER)

        settings = self.subject.execute(ACCOUNT_ID, now=LATER_ANSWER)

        assert settings.invite_status is StreakReminderInviteStatus.ANSWERED
        assert self.profile.reminder_invite_answered_at == FIRST_ANSWER
        self.repositories.profiles.update.assert_not_called()

    def test_should_not_change_the_hour_xp_or_streak(self) -> None:
        self._given_profile()

        self.subject.execute(ACCOUNT_ID, now=FIRST_ANSWER)

        assert self.profile.reminder_hour == 19
        assert self.profile.total_xp == 0
        assert self.profile.streak == PracticeStreak(
            current=1, longest=1, latest_practice_date=date(2026, 9, 14)
        )
        self.repositories.events.add.assert_not_called()

    def test_should_fail_when_the_account_has_no_profile(self) -> None:
        self.repositories.profiles.find_by_account_id_for_update.return_value = None

        with pytest.raises(GamificationProfileNotFoundError):
            self.subject.execute(ACCOUNT_ID, now=FIRST_ANSWER)

        self.repositories.profiles.update.assert_not_called()
