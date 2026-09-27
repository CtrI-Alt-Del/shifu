from shifu.curriculum.core.domain.errors import InvalidEvaluationRuleError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import require_non_empty, require_weight_total

from .code_rubric_criterion import CodeRubricCriterion


@structure
class CodeRubricEvaluationPart:
    question_key: str
    weight_percentage: int
    criteria: tuple[CodeRubricCriterion, ...]

    def __post_init__(self) -> None:
        require_non_empty(self.question_key, InvalidEvaluationRuleError)
        require_weight_total(
            (criterion.weight_percentage for criterion in self.criteria),
            InvalidEvaluationRuleError,
        )
        if len(self.criteria) != len({criterion.key for criterion in self.criteria}):
            raise InvalidEvaluationRuleError
        if not any(criterion.required for criterion in self.criteria):
            raise InvalidEvaluationRuleError
