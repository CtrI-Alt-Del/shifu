from typing import Protocol

from shifu.intelligence.core.domain.structures.planning_intent_classification import (
    PlanningIntentClassification,
)
from shifu.intelligence.core.domain.structures.planning_query import PlanningQuery


class PlanningIntentClassifierProvider(Protocol):
    def classify(self, query: PlanningQuery) -> PlanningIntentClassification:
        """Decide learning, out-of-scope or ambiguous; raise on technical failure."""
        ...
