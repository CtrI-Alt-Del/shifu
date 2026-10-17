from datetime import UTC, date, datetime
from unittest.mock import create_autospec

import pytest

from shifu.fakers.gamification.entities import GamificationProfileFaker
from shifu.gamification.core.domain.enums import CalendarDayState
from shifu.gamification.core.domain.errors import (
    GamificationProfileNotFoundError,
    InvalidGamificationError,
)
from shifu.gamification.core.domain.structures import PracticeCalendar, PracticeStreak
from shifu.gamification.core.interfaces import (
    GamificationDatabase,
    GamificationDatabaseRepositories,
)
from shifu.gamification.core.use_cases import GetPracticeCalendarUseCase

ACCOUNT_ID = 'account-1'
SAO_PAULO = 'America/Sao_Paulo'


class TestGetPracticeCalendarUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(GamificationDatabase, instance=True)
        self.repositories = create_autospec(
            GamificationDatabaseRepositories, instance=True
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.repositories.profiles.find_by_account_id.return_value = (
            GamificationProfileFaker.fake(
                account_id=ACCOUNT_ID,
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                streak=PracticeStreak(
                    current=2, longest=5, latest_practice_date=date(2026, 9, 10)
                ),
            )
        )
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = ()
        self.subject = GetPracticeCalendarUseCase(self.database)

    def _read(
        self,
        *,
        now: datetime,
        year: int = 2026,
        month: int = 9,
        time_zone: str | None = 'UTC',
    ) -> PracticeCalendar:
        return self.subject.execute(
            ACCOUNT_ID, year, month, time_zone=time_zone, now=now
        )

    @staticmethod
    def _state_on(calendar: PracticeCalendar, day: int) -> CalendarDayState:
        return next(item.state for item in calendar.days if item.day.day == day)

    def test_should_reject_a_month_after_the_current_month(self) -> None:
        with pytest.raises(InvalidGamificationError):
            self._read(now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC), month=10)

    def test_should_reject_an_out_of_range_month(self) -> None:
        with pytest.raises(InvalidGamificationError):
            self._read(now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC), month=13)

    def test_should_reject_when_the_account_has_no_profile(self) -> None:
        self.repositories.profiles.find_by_account_id.return_value = None

        with pytest.raises(GamificationProfileNotFoundError):
            self._read(now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC))

    def test_should_emit_one_ordered_day_per_day_of_the_month(self) -> None:
        calendar = self._read(now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC))

        assert len(calendar.days) == 30
        assert [item.day.day for item in calendar.days] == list(range(1, 31))
        assert calendar.today == date(2026, 9, 15)

    def test_should_derive_the_five_day_states(self) -> None:
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 9, 2),
            date(2026, 9, 9),
            date(2026, 9, 10),
        )

        calendar = self._read(now=datetime(2026, 9, 11, 12, 0, tzinfo=UTC))

        assert self._state_on(calendar, 1) == CalendarDayState.NEUTRAL
        assert self._state_on(calendar, 2) == CalendarDayState.PRACTICED
        assert self._state_on(calendar, 5) == CalendarDayState.MISSED
        assert self._state_on(calendar, 9) == CalendarDayState.CURRENT_STREAK
        assert self._state_on(calendar, 10) == CalendarDayState.CURRENT_STREAK
        assert self._state_on(calendar, 11) == CalendarDayState.TODAY_PENDING
        assert self._state_on(calendar, 12) == CalendarDayState.NEUTRAL
        assert calendar.earliest_practice_date == date(2026, 9, 2)

    def test_should_keep_a_streak_held_through_yesterday_active_today(self) -> None:
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 9, 6),
            date(2026, 9, 7),
            date(2026, 9, 8),
            date(2026, 9, 9),
            date(2026, 9, 10),
        )

        calendar = self._read(now=datetime(2026, 9, 11, 12, 0, tzinfo=UTC))

        assert calendar.streak.current == 5
        assert self._state_on(calendar, 11) == CalendarDayState.TODAY_PENDING

    def test_should_decay_the_current_streak_once_a_whole_day_passed(self) -> None:
        """Same stored rows, later `now`: the run is no longer current."""
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 9, 6),
            date(2026, 9, 7),
            date(2026, 9, 8),
            date(2026, 9, 9),
            date(2026, 9, 10),
        )

        calendar = self._read(now=datetime(2026, 9, 12, 12, 0, tzinfo=UTC))

        assert calendar.streak.current == 0
        assert calendar.streak.longest == 5
        assert self._state_on(calendar, 10) == CalendarDayState.PRACTICED

    def test_should_report_the_stored_longest_when_no_day_is_recorded(self) -> None:
        calendar = self._read(now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC))

        assert calendar.streak.current == 0
        assert calendar.streak.longest == 5
        assert calendar.earliest_practice_date is None
        assert all(item.state == CalendarDayState.NEUTRAL for item in calendar.days)

    def test_should_resolve_today_in_the_viewer_time_zone(self) -> None:
        """02:30Z on 1 October is still 30 September in Sao Paulo."""
        calendar = self._read(
            now=datetime(2026, 10, 1, 2, 30, tzinfo=UTC), time_zone=SAO_PAULO
        )

        assert calendar.today == date(2026, 9, 30)

    def test_should_fall_back_to_utc_for_an_unusable_viewer_zone(self) -> None:
        calendar = self._read(
            now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC), time_zone='Mars/Olympus'
        )

        assert calendar.today == date(2026, 9, 15)

    def test_should_not_mutate_practice_days_on_a_read(self) -> None:
        """Removing a Goal or Skill cannot disturb recognized days."""
        self._read(now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC))

        self.repositories.practice_days.try_add.assert_not_called()
        self.repositories.practice_days.remove_many_by_account_id.assert_not_called()
        self.repositories.profiles.update.assert_not_called()

    def test_should_derive_longest_from_the_days_when_the_snapshot_lags(self) -> None:
        """A profile whose snapshot was never written must not report a
        shorter longest streak than the recorded days already prove."""
        self.repositories.profiles.find_by_account_id.return_value = (
            GamificationProfileFaker.fake(
                account_id=ACCOUNT_ID,
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                streak=PracticeStreak(),
            )
        )
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 9, 1),
            date(2026, 9, 2),
            date(2026, 9, 3),
            date(2026, 9, 4),
        )

        calendar = self._read(now=datetime(2026, 9, 20, 12, 0, tzinfo=UTC))

        assert calendar.streak.longest == 4
        assert calendar.streak.current == 0
        assert calendar.streak.latest_practice_date == date(2026, 9, 4)

    def test_should_keep_the_longest_run_when_it_is_not_the_current_one(self) -> None:
        self.repositories.profiles.find_by_account_id.return_value = (
            GamificationProfileFaker.fake(
                account_id=ACCOUNT_ID,
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                streak=PracticeStreak(),
            )
        )
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 9, 1),
            date(2026, 9, 2),
            date(2026, 9, 3),
            date(2026, 9, 4),
            date(2026, 9, 14),
            date(2026, 9, 15),
        )

        calendar = self._read(now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC))

        assert calendar.streak.longest == 4
        assert calendar.streak.current == 2

    def test_should_count_a_run_ending_exactly_today_as_current(self) -> None:
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 9, 14),
            date(2026, 9, 15),
        )

        calendar = self._read(now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC))

        assert calendar.streak.current == 2
        assert self._state_on(calendar, 15) == CalendarDayState.CURRENT_STREAK

    def test_should_count_a_single_day_run(self) -> None:
        self.repositories.profiles.find_by_account_id.return_value = (
            GamificationProfileFaker.fake(
                account_id=ACCOUNT_ID,
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                streak=PracticeStreak(),
            )
        )
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 9, 15),
        )

        calendar = self._read(now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC))

        assert calendar.streak.current == 1
        assert calendar.streak.longest == 1

    def test_should_reject_a_month_below_the_valid_range(self) -> None:
        with pytest.raises(InvalidGamificationError):
            self._read(now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC), month=0)

    def test_should_reject_a_year_below_the_valid_range(self) -> None:
        with pytest.raises(InvalidGamificationError):
            self._read(now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC), year=0, month=1)

    def test_should_reject_a_later_year_even_for_an_earlier_month(self) -> None:
        with pytest.raises(InvalidGamificationError):
            self._read(now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC), year=2027, month=1)

    def test_should_accept_the_current_month_itself(self) -> None:
        calendar = self._read(now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC), month=9)

        assert calendar.month == 9
        assert len(calendar.days) == 30

    def test_should_size_a_month_from_the_real_calendar(self) -> None:
        calendar = self._read(now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC), month=2)

        assert len(calendar.days) == 28
        assert calendar.days[0].day == date(2026, 2, 1)
        assert calendar.days[-1].day == date(2026, 2, 28)

    def test_should_accept_january_and_december(self) -> None:
        january = self._read(now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC), month=1)
        december = self._read(
            now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC), year=2025, month=12
        )

        assert january.month == 1
        assert len(january.days) == 31
        assert december.month == 12
        assert len(december.days) == 31

    def test_should_scope_every_read_to_the_requested_account(self) -> None:
        self._read(now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC))

        self.repositories.profiles.find_by_account_id.assert_called_once_with(
            ACCOUNT_ID
        )
        self.repositories.practice_days.find_many_dates_by_account_id.assert_called_once_with(
            ACCOUNT_ID
        )

    def test_should_not_inflate_a_run_that_follows_a_gap(self) -> None:
        self.repositories.profiles.find_by_account_id.return_value = (
            GamificationProfileFaker.fake(
                account_id=ACCOUNT_ID,
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                streak=PracticeStreak(),
            )
        )
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 9, 1),
            date(2026, 9, 3),
            date(2026, 9, 4),
        )

        calendar = self._read(now=datetime(2026, 9, 20, 12, 0, tzinfo=UTC))

        assert calendar.streak.longest == 2

    def test_should_count_an_isolated_current_day_as_a_streak_of_one(self) -> None:
        self.repositories.profiles.find_by_account_id.return_value = (
            GamificationProfileFaker.fake(
                account_id=ACCOUNT_ID,
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                streak=PracticeStreak(),
            )
        )
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 9, 1),
            date(2026, 9, 15),
        )

        calendar = self._read(now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC))

        assert calendar.streak.current == 1
        assert self._state_on(calendar, 1) == CalendarDayState.PRACTICED

    def test_should_reject_an_out_of_range_month_in_a_past_year(self) -> None:
        """The range guard must stand on its own: a past year skips the
        future-month check, so month 13 would otherwise reach the calendar."""
        with pytest.raises(InvalidGamificationError):
            self._read(
                now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC), year=2025, month=13
            )
