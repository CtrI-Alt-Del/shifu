from decimal import Decimal

from shifu.learning.core.domain.enums import CompetencyProgressStatus
from shifu.shared.core.domain.structures import structure


@structure
class DiagnosticCompetencySummary:
    competency_id: str
    competency_name: str
    position: int = 1
    progress: Decimal | None = None
    coverage_complete: bool = False
    status: CompetencyProgressStatus | None = None
    is_focus: bool = False
    content_released: bool = False
