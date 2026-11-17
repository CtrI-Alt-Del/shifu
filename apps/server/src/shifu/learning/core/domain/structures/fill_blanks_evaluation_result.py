from decimal import Decimal
from typing import Literal

from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.shared.core.domain.structures import Percentage, structure


@structure
class FillBlanksEvaluationResult:
    question_key: str
    score: Decimal
    is_correct: bool
    correct_blank_keys: tuple[str, ...]
    blank_count: int
    explanation: str
    kind: Literal['fill_blanks'] = 'fill_blanks'

    def __post_init__(self) -> None:
        Percentage.create(self.score, error_type=InvalidAttemptError)
        if self.blank_count < 1 or len(self.correct_blank_keys) > self.blank_count:
            raise InvalidAttemptError
