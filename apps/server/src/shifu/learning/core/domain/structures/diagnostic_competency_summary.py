from decimal import Decimal

from shifu.shared.core.domain.structures import structure


@structure
class DiagnosticCompetencySummary:
    competency_id: str
    competency_name: str
    progress: Decimal | None
