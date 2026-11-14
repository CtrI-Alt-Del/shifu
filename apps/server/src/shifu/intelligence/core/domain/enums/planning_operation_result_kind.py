from enum import StrEnum


class PlanningOperationResultKind(StrEnum):
    BATCH = 'batch'
    PROPOSAL = 'proposal'
    OUT_OF_SCOPE = 'out-of-scope'
    UNSUPPORTED = 'unsupported'
    VALIDATION_FAILED = 'validation-failed'
    FAILED = 'failed'
