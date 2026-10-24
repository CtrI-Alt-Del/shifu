from datetime import date

from shifu.gamification.core.domain.enums.calendar_day_state import CalendarDayState


def practice_day_state(
    day: date,
    *,
    today: date,
    earliest: date | None,
    practiced: frozenset[date],
    current_run: frozenset[date],
) -> CalendarDayState:
    """Which of the five states one day carries for this viewer's today.

    Shared by the monthly calendar and the overview's trailing-seven-day strip
    so one date is never classified differently by the two surfaces.
    """
    if day > today or earliest is None or day < earliest:
        return CalendarDayState.NEUTRAL
    if day in practiced:
        if day in current_run:
            return CalendarDayState.CURRENT_STREAK
        return CalendarDayState.PRACTICED
    if day == today:
        return CalendarDayState.TODAY_PENDING
    return CalendarDayState.MISSED
