from calendar import monthrange
from datetime import date, datetime
from zoneinfo import ZoneInfo

from shifu.gamification.core.domain.current_practice_run import current_practice_run
from shifu.gamification.core.domain.derived_practice_streak import (
    derived_practice_streak,
)
from shifu.gamification.core.domain.errors import InvalidGamificationError
from shifu.gamification.core.domain.practice_day_state import practice_day_state
from shifu.gamification.core.domain.resolved_time_zone import resolved_time_zone
from shifu.gamification.core.domain.structures import (
    CalendarDay,
    PracticeCalendar,
    PracticeStreak,
)
from shifu.gamification.core.interfaces import GamificationDatabase


class GetPracticeCalendarUseCase:
    """Build one month of practice-day states for the owning account.

    The day-state, streak and time-zone rules live in `core/domain` so the
    overview read applies exactly the same ones over its own window.
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

        zone = resolved_time_zone(time_zone)
        today = now.astimezone(ZoneInfo(zone)).date()
        if (year, month) > (today.year, today.month):
            raise InvalidGamificationError

        with self._database.transaction() as repositories:
            profile = repositories.profiles.find_by_account_id(account_id)
            dates = repositories.practice_days.find_many_dates_by_account_id(account_id)

        # An account whose profile row has not been created yet reads the
        # initial state rather than an error, as the overview does: JN-01
        # describes that state as normal.
        stored_streak = profile.streak if profile is not None else PracticeStreak()

        ordered = tuple(sorted(set(dates)))
        earliest = ordered[0] if ordered else None
        practiced = frozenset(ordered)
        run = current_practice_run(ordered, today=today)
        run_dates = frozenset(run)

        days = tuple(
            CalendarDay(
                day=day,
                state=practice_day_state(
                    day,
                    today=today,
                    earliest=earliest,
                    practiced=practiced,
                    current_run=run_dates,
                ),
            )
            for day in self._days_of_month(year, month)
        )

        return PracticeCalendar(
            year=year,
            month=month,
            today=today,
            days=days,
            streak=derived_practice_streak(
                stored_streak, ordered_dates=ordered, current_run=run
            ),
            earliest_practice_date=earliest,
        )

    @staticmethod
    def _days_of_month(year: int, month: int) -> tuple[date, ...]:
        _, length = monthrange(year, month)
        return tuple(date(year, month, day) for day in range(1, length + 1))
