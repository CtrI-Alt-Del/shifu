from decimal import Decimal

from shifu.learning.core.domain.structures.qualitative_criterion_result import (
    QualitativeCriterionResult,
)
from shifu.shared.core.domain.structures import structure


@structure
class QualitativeEvaluationResult:
    question_key: str
    score: Decimal
    criteria: tuple[QualitativeCriterionResult, ...]
