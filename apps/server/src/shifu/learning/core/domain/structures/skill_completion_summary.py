from datetime import datetime
from decimal import Decimal

from shifu.learning.core.domain.structures.competency_completion_summary import (
    CompetencyCompletionSummary,
)
from shifu.shared.core.domain.structures import structure
from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.shared.core.domain.validation import require_percentage


@structure
class SkillCompletionSummary:
    competencies: tuple[CompetencyCompletionSummary, ...]
    initial_progress: Decimal | None
    final_progress: Decimal
    started_at: datetime
    completed_at: datetime

    def __post_init__(self) -> None:
        if self.initial_progress is not None:
            require_percentage(self.initial_progress, InvalidAttemptError)
        require_percentage(self.final_progress, InvalidAttemptError)
        if self.completed_at < self.started_at:
            raise InvalidAttemptError
