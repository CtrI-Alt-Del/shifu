from decimal import Decimal

from shifu.shared.core.domain.structures import structure
from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.shared.core.domain.validation import require_percentage


@structure
class ChoiceEvaluationResult:
    question_key: str
    score: Decimal
    is_correct: bool
    explanation: str

    def __post_init__(self) -> None:
        require_percentage(self.score, InvalidAttemptError)
