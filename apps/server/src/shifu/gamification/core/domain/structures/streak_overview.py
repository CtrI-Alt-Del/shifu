from datetime import date

from shifu.gamification.core.domain.structures.calendar_day import CalendarDay
from shifu.gamification.core.domain.structures.practice_streak import PracticeStreak
from shifu.shared.core.domain.structures import structure


@structure
class StreakOverview:
    """The overview's constância block; not a persisted entity.

    `last_seven_days` holds exactly seven days, oldest first and ending
    today, each carrying the same five states the monthly calendar uses.
    """

    streak: PracticeStreak
    last_seven_days: tuple[CalendarDay, ...]
    today: date
    is_today_pending: bool
