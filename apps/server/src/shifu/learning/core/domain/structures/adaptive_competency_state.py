from datetime import datetime
from decimal import Decimal

from shifu.learning.core.domain.enums import CompetencyProgressStatus
from shifu.shared.core.domain.structures import structure


@structure
class AdaptiveCompetencyState:
    competency_id: str
    progress: Decimal | None
    partial_progress: Decimal | None
    coverage_complete: bool
    status: CompetencyProgressStatus
    mastered_at: datetime | None
    verification_cause: str | None
    verification_concept_id: str | None
    content_released: bool
