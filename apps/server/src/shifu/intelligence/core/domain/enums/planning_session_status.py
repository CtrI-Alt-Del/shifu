from enum import StrEnum


class PlanningSessionStatus(StrEnum):
    PROCESSING = 'processing'
    INTERVIEW = 'interview'
    PROPOSAL = 'proposal'
    OUT_OF_SCOPE = 'out-of-scope'
    UNSUPPORTED = 'unsupported'
    VALIDATION_FAILED = 'validation-failed'
    FAILED = 'failed'
