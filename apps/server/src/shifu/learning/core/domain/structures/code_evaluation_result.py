from decimal import Decimal

from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.learning.core.domain.structures.code_case_result import CodeCaseResult
from shifu.shared.core.domain.structures import Percentage, structure


@structure
class CodeEvaluationResult:
    question_key: str
    score: Decimal
    cases: tuple[CodeCaseResult, ...]
    standard_output: str
    standard_error: str

    def __post_init__(self) -> None:
        Percentage.create(self.score, error_type=InvalidAttemptError)
