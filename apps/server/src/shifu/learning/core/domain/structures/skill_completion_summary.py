from datetime import datetime
from decimal import Decimal

from shifu.learning.core.domain.structures.competency_completion_summary import (
    CompetencyCompletionSummary,
)
from shifu.shared.core.domain.structures import structure


@structure
class SkillCompletionSummary:
    competencies: tuple[CompetencyCompletionSummary, ...]
    initial_progress: Decimal
    final_progress: Decimal
    started_at: datetime
    completed_at: datetime
