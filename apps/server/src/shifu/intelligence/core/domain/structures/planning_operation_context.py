from shifu.intelligence.core.domain.enums.planning_intent_kind import (
    PlanningIntentKind,
)
from shifu.intelligence.core.domain.structures.planning_answered_batch import (
    PlanningAnsweredBatch,
)
from shifu.shared.core.domain.structures import structure


@structure
class PlanningOperationContext:
    """Everything a workflow run may read about one planning operation."""

    planning_id: str
    operation_id: str
    generation: int
    account_id: str
    intent: str
    answered_batches: tuple[PlanningAnsweredBatch, ...]
    classification: PlanningIntentKind | None

    @property
    def answers(self) -> tuple[str, ...]:
        """Flatten the selected alternatives for the retrieval query."""
        return tuple(
            text
            for batch in self.answered_batches
            for item in batch.items
            for text in item.selected_texts
        )
