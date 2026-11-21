from decimal import Decimal
from typing import Literal

from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.shared.core.domain.structures import Percentage, structure


@structure
class PairMatchingEvaluationResult:
    question_key: str
    score: Decimal
    correct_pair_count: int
    total_pair_count: int
    outcome: Literal['full', 'partial', 'incorrect']
    explanation: str

    def __post_init__(self) -> None:
        Percentage.create(self.score, error_type=InvalidAttemptError)
        if (
            self.total_pair_count < 1
            or not 0 <= self.correct_pair_count <= self.total_pair_count
        ):
            raise InvalidAttemptError
