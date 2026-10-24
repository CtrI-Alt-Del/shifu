from math import isfinite

from shifu.intelligence.core.domain.enums.planning_intent_kind import (
    PlanningIntentKind,
)
from shifu.shared.core.domain.structures import structure


@structure
class PlanningIntentClassification:
    kind: PlanningIntentKind
    confidence: float
    probabilities: tuple[tuple[str, float], ...]

    def __post_init__(self) -> None:
        if not isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise ValueError('Classification confidence must be within [0, 1].')
        labels = [label for label, _ in self.probabilities]
        if sorted(labels) != sorted(kind.value for kind in PlanningIntentKind):
            raise ValueError('Probabilities must cover exactly the planning kinds.')
        values = [value for _, value in self.probabilities]
        if any(not isfinite(value) or not 0 <= value <= 1 for value in values):
            raise ValueError('Each probability must be within [0, 1].')
        if abs(sum(values) - 1) > 0.02:
            raise ValueError('Probabilities must sum to one.')
