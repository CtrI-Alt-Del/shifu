from datetime import datetime
from decimal import Decimal

from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.learning.core.domain.structures.competency_completion_summary import (
    CompetencyCompletionSummary,
)
from shifu.shared.core.domain.structures import Percentage, structure


@structure
class SkillCompletionSummary:
    competencies: tuple[CompetencyCompletionSummary, ...]
    initial_progress: Decimal | None
    final_progress: Decimal
    started_at: datetime
    completed_at: datetime
    initial_coverage_complete: bool = True

    def __post_init__(self) -> None:
        if self.initial_progress is not None:
            Percentage.create(self.initial_progress, error_type=InvalidAttemptError)
        Percentage.create(self.final_progress, error_type=InvalidAttemptError)
        if self.completed_at < self.started_at:
            raise InvalidAttemptError
