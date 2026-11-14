from enum import StrEnum


class PlanningIntentKind(StrEnum):
    LEARNING = 'learning'
    OUT_OF_SCOPE = 'out-of-scope'
    AMBIGUOUS = 'ambiguous'
