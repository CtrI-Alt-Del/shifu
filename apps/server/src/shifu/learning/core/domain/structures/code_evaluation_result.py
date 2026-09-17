from decimal import Decimal

from shifu.learning.core.domain.structures.code_case_result import CodeCaseResult
from shifu.shared.core.domain.structures import structure
from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.shared.core.domain.validation import require_percentage


@structure
class CodeEvaluationResult:
    question_key: str
    score: Decimal
    cases: tuple[CodeCaseResult, ...]
    standard_output: str
    standard_error: str

    def __post_init__(self) -> None:
        require_percentage(self.score, InvalidAttemptError)
