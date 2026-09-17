from decimal import Decimal

from shifu.shared.core.domain.structures import structure
from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.shared.core.domain.validation import require_percentage


@structure
class CompetencyCompletionSummary:
    competency_id: str
    initial_progress: Decimal
    final_progress: Decimal

    def __post_init__(self) -> None:
        require_percentage(self.initial_progress, InvalidAttemptError)
        require_percentage(self.final_progress, InvalidAttemptError)
