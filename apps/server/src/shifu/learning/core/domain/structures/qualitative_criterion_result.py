from decimal import Decimal

from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.shared.core.domain.structures import Percentage, structure


@structure
class QualitativeCriterionResult:
    criterion_key: str
    score: Decimal
    explanation: str

    def __post_init__(self) -> None:
        Percentage.create(self.score, error_type=InvalidAttemptError)
