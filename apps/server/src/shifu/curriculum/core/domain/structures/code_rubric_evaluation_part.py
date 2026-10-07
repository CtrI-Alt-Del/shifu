from shifu.curriculum.core.domain.errors import InvalidEvaluationRuleError
from shifu.shared.core.domain.structures import (
    NonEmptyText,
    WeightDistribution,
    structure,
)

from .code_rubric_criterion import CodeRubricCriterion


@structure
class CodeRubricEvaluationPart:
    question_key: str
    weight_percentage: int
    criteria: tuple[CodeRubricCriterion, ...]

    def __post_init__(self) -> None:
        NonEmptyText.create(self.question_key, error_type=InvalidEvaluationRuleError)
        WeightDistribution.create(
            (criterion.weight_percentage for criterion in self.criteria),
            error_type=InvalidEvaluationRuleError,
        )
        if len(self.criteria) != len({criterion.key for criterion in self.criteria}):
            raise InvalidEvaluationRuleError

        if not any(criterion.required for criterion in self.criteria):
            raise InvalidEvaluationRuleError
