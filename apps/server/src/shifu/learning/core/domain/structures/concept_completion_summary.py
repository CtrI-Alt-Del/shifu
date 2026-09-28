from decimal import Decimal

from shifu.learning.core.domain.enums import ActivityDifficulty
from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import require_percentage


@structure
class ConceptCompletionSummary:
    concept_id: str
    initial_progress: Decimal | None
    final_progress: Decimal
    initial_observed_difficulties: tuple[ActivityDifficulty, ...] = ()
    final_observed_difficulties: tuple[ActivityDifficulty, ...] = ()

    def __post_init__(self) -> None:
        if self.initial_progress is not None:
            require_percentage(self.initial_progress, InvalidAttemptError)
        require_percentage(self.final_progress, InvalidAttemptError)
