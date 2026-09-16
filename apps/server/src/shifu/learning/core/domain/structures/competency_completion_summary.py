from decimal import Decimal

from shifu.shared.core.domain.structures import structure


@structure
class CompetencyCompletionSummary:
    competency_id: str
    initial_progress: Decimal
    final_progress: Decimal
