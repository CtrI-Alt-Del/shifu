from enum import StrEnum


class StreakReminderInviteStatus(StrEnum):
    NOT_ELIGIBLE = 'not-eligible'
    PENDING = 'pending'
    ANSWERED = 'answered'
