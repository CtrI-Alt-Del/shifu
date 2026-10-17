from datetime import date

from shifu.gamification.core.domain.errors import InvalidGamificationError
from shifu.gamification.core.domain.structures.calendar_day import CalendarDay
from shifu.gamification.core.domain.structures.practice_streak import PracticeStreak
from shifu.shared.core.domain.structures import BoundedInteger, structure


@structure
class PracticeCalendar:
    year: int
    month: int
    today: date
    days: tuple[CalendarDay, ...]
    streak: PracticeStreak
    earliest_practice_date: date | None = None

    def __post_init__(self) -> None:
        BoundedInteger.create(self.year, minimum=1, error_type=InvalidGamificationError)
        BoundedInteger.create(
            self.month, minimum=1, maximum=12, error_type=InvalidGamificationError
        )
        if type(self.today) is not date:
            raise InvalidGamificationError
        if type(self.streak) is not PracticeStreak:
            raise InvalidGamificationError
        if self.earliest_practice_date is not None and (
            type(self.earliest_practice_date) is not date
        ):
            raise InvalidGamificationError
        for day in self.days:
            if type(day) is not CalendarDay:
                raise InvalidGamificationError
            if day.day.year != self.year or day.day.month != self.month:
                raise InvalidGamificationError
