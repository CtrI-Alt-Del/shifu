from datetime import date

from shifu.gamification.core.domain.structures.calendar_day import CalendarDay
from shifu.gamification.core.domain.structures.practice_streak import PracticeStreak
from shifu.shared.core.domain.structures import structure


@structure
class StreakOverview:
    """The overview's constância block; not a persisted entity.

    `current_month` holds every day of the viewer's current local month,
    oldest first, each carrying the same five states the monthly calendar uses.
    """

    streak: PracticeStreak
    current_month: tuple[CalendarDay, ...]
    today: date
