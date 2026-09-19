from decimal import Decimal

from shifu.learning.core.domain.structures.qualitative_criterion_result import (
    QualitativeCriterionResult,
)
from shifu.shared.core.domain.structures import structure
from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.shared.core.domain.validation import require_percentage


@structure
class QualitativeEvaluationResult:
    question_key: str
    score: Decimal
    criteria: tuple[QualitativeCriterionResult, ...]

    def __post_init__(self) -> None:
        require_percentage(self.score, InvalidAttemptError)
