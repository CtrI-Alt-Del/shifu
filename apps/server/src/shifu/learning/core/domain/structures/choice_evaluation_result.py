from decimal import Decimal

from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.shared.core.domain.structures import Percentage, structure


@structure
class ChoiceEvaluationResult:
    question_key: str
    score: Decimal
    is_correct: bool
    explanation: str

    def __post_init__(self) -> None:
        Percentage.create(self.score, error_type=InvalidAttemptError)
