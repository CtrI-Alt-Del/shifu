from decimal import Decimal

from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.learning.core.domain.structures.concept_completion_summary import (
    ConceptCompletionSummary,
)
from shifu.shared.core.domain.structures import Percentage, structure


@structure
class CompetencyCompletionSummary:
    competency_id: str
    initial_progress: Decimal | None
    final_progress: Decimal
    initial_coverage_complete: bool = True
    concepts: tuple[ConceptCompletionSummary, ...] = ()

    def __post_init__(self) -> None:
        if self.initial_progress is not None:
            Percentage.create(self.initial_progress, error_type=InvalidAttemptError)
        Percentage.create(self.final_progress, error_type=InvalidAttemptError)
