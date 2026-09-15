from decimal import Decimal

from shifu.shared.core.domain.structures import structure


@structure
class QualitativeCriterionResult:
    criterion_key: str
    score: Decimal
    explanation: str
