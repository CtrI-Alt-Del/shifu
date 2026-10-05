from datetime import date

from shifu.gamification.core.domain.errors import InvalidGamificationError
from shifu.shared.core.domain.structures import BoundedInteger, structure


@structure
class PracticeStreak:
    current: int = 0
    longest: int = 0
    latest_practice_date: date | None = None

    def __post_init__(self) -> None:
        BoundedInteger.create(self.current, error_type=InvalidGamificationError)
        BoundedInteger.create(self.longest, error_type=InvalidGamificationError)
        if self.current > self.longest:
            raise InvalidGamificationError
        if self.latest_practice_date is not None and (
            type(self.latest_practice_date) is not date
        ):
            raise InvalidGamificationError
        if (self.longest == 0) != (self.latest_practice_date is None):
            raise InvalidGamificationError
