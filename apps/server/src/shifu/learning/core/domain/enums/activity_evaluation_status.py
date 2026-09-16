from enum import StrEnum


class ActivityEvaluationStatus(StrEnum):
    PENDING = 'pending'
    FAILED = 'failed'
    COMPLETED = 'completed'
