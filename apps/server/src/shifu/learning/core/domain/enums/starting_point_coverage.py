from enum import StrEnum


class StartingPointCoverage(StrEnum):
    COMPLETE = 'complete'
    PARTIAL = 'partial'
    UNKNOWN = 'unknown'
