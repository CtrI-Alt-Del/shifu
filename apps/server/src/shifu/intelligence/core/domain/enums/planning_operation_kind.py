from enum import StrEnum


class PlanningOperationKind(StrEnum):
    START = 'start'
    ANSWER = 'answer'
    RESTART = 'restart'
    RETRY = 'retry'
