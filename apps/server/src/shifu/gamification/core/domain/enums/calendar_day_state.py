from enum import StrEnum


class CalendarDayState(StrEnum):
    NEUTRAL = 'neutral'
    PRACTICED = 'practiced'
    CURRENT_STREAK = 'current-streak'
    MISSED = 'missed'
    TODAY_PENDING = 'today-pending'
