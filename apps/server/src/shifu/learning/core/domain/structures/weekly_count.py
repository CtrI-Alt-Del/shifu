from datetime import date

from shifu.shared.core.domain.structures import structure


@structure
class WeeklyCount:
    week_start: date  # local Monday
    count: int
