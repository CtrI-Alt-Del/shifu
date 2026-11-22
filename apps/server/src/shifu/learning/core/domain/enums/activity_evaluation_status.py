from enum import StrEnum


class ActivityEvaluationStatus(StrEnum):
    PENDING = 'pending'
    FAILED = 'failed'
    COMPLETED = 'completed'
    CLOSED_WITHOUT_GRADE = 'closed_without_grade'
