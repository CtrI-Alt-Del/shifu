from enum import StrEnum


class StreakReminderStatus(StrEnum):
    PENDING = 'pending'
    SENT = 'sent'
    SKIPPED = 'skipped'
    EXPIRED = 'expired'
    CANCELLED = 'cancelled'
    FAILED = 'failed'
