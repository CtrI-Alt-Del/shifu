from enum import StrEnum


class MentorResponseEventKind(StrEnum):
    STATUS = 'status'
    CONSULTATION = 'consultation'
    BLOCK = 'block'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
