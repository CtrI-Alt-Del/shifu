from calendar import monthrange
from datetime import date, datetime, timedelta
from itertools import pairwise
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from shifu.gamification.core.domain.enums import CalendarDayState
from shifu.gamification.core.domain.errors import (
    GamificationProfileNotFoundError,
    InvalidGamificationError,
)
from shifu.gamification.core.domain.structures import (
    CalendarDay,
    PracticeCalendar,
    PracticeStreak,
)
from shifu.gamification.core.interfaces import GamificationDatabase

_FALLBACK_TIME_ZONE = 'UTC'


def _resolve_time_zone(time_zone: str | None) -> str:
    if not time_zone:
        return _FALLBACK_TIME_ZONE
    try:
        ZoneInfo(time_zone)
    except (ZoneInfoNotFoundError, ValueError):
        return _FALLBACK_TIME_ZONE
    return time_zone


def _current_run(ordered: list[date], *, today: date) -> tuple[date, ...]:
    """The consecutive run ending today or yesterday, empty when broken."""
    if not ordered:
        return ()
    latest = ordered[-1]
    if latest not in (today, today - timedelta(days=1)):
        return ()
    index = len(ordered) - 1
    while index > 0 and (ordered[index] - ordered[index - 1]).days == 1:
        index -= 1
    return tuple(ordered[index:])


def _longest_run(ordered: list[date]) -> int:
    if not ordered:
        return 0
    longest = 1
    run = 1
    for previous, following in pairwise(ordered):
        run = run + 1 if (following - previous).days == 1 else 1
        longest = max(longest, run)
    return longest


class GetPracticeCalendarUseCase:
    """Build one month of practice-day states for the owning account.

    `current` is derived here against the viewer's today rather than read
    from the profile snapshot, because a streak decays with the passage of
    time and no stored column can stay correct without a write. `longest`
    stays the stored fact.
    """

    def __init__(self, database: GamificationDatabase) -> None:
        self._database = database

    def execute(
        self,
        account_id: str,
        year: int,
        month: int,
        *,
        time_zone: str | None,
        now: datetime,
    ) -> PracticeCalendar:
        if month < 1 or month > 12 or year < 1:
            raise InvalidGamificationError

        zone = _resolve_time_zone(time_zone)
        today = now.astimezone(ZoneInfo(zone)).date()
        if (year, month) > (today.year, today.month):
            raise InvalidGamificationError

        with self._database.transaction() as repositories:
            profile = repositories.profiles.find_by_account_id(account_id)
            if profile is None:
                raise GamificationProfileNotFoundError

            dates = repositories.practice_days.find_many_dates_by_account_id(account_id)

        ordered = sorted(set(dates))
        earliest = ordered[0] if ordered else None
        practiced = set(ordered)
        run = set(_current_run(ordered, today=today))

        days = tuple(
            CalendarDay(
                day=day,
                state=self._state_for(
                    day, today=today, earliest=earliest, practiced=practiced, run=run
                ),
            )
            for day in self._days_of_month(year, month)
        )

        return PracticeCalendar(
            year=year,
            month=month,
            today=today,
            days=days,
            streak=self._streak_for(profile.streak, ordered, run),
            earliest_practice_date=earliest,
        )

    @staticmethod
    def _days_of_month(year: int, month: int) -> tuple[date, ...]:
        _, length = monthrange(year, month)
        return tuple(date(year, month, day) for day in range(1, length + 1))

    @staticmethod
    def _state_for(
        day: date,
        *,
        today: date,
        earliest: date | None,
        practiced: set[date],
        run: set[date],
    ) -> CalendarDayState:
        if day > today or earliest is None or day < earliest:
            return CalendarDayState.NEUTRAL
        if day in practiced:
            if day in run:
                return CalendarDayState.CURRENT_STREAK
            return CalendarDayState.PRACTICED
        if day == today:
            return CalendarDayState.TODAY_PENDING
        return CalendarDayState.MISSED

    @staticmethod
    def _streak_for(
        stored: PracticeStreak, ordered: list[date], run: set[date]
    ) -> PracticeStreak:
        if not ordered:
            return PracticeStreak(
                current=0,
                longest=stored.longest,
                latest_practice_date=stored.latest_practice_date,
            )
        # `longest` stays the stored fact, but it can never fall below what the
        # recorded days already prove — a profile whose snapshot was never
        # written would otherwise report longest 0 beside a real latest date,
        # which `PracticeStreak` rejects.
        return PracticeStreak(
            current=len(run),
            longest=max(stored.longest, _longest_run(ordered)),
            latest_practice_date=ordered[-1],
        )
