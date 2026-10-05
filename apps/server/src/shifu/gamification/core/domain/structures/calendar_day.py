from datetime import date

from shifu.gamification.core.domain.enums.calendar_day_state import CalendarDayState
from shifu.gamification.core.domain.errors import InvalidGamificationError
from shifu.shared.core.domain.structures import EnumValue, structure


@structure
class CalendarDay:
    day: date
    state: CalendarDayState

    def __post_init__(self) -> None:
        if type(self.day) is not date:
            raise InvalidGamificationError
        EnumValue.create(
            self.state, CalendarDayState, error_type=InvalidGamificationError
        )
