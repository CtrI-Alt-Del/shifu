from enum import StrEnum


class ActivityAttemptKind(StrEnum):
    DIAGNOSTIC = 'diagnostic'
    LEARNING = 'learning'
    REVIEW = 'review'
