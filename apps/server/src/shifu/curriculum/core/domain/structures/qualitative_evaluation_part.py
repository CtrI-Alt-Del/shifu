from shifu.shared.core.domain.structures import structure
from shifu.curriculum.core.domain.errors import InvalidEvaluationRuleError
from shifu.shared.core.domain.validation import require_weight_total

from .qualitative_criterion import QualitativeCriterion


@structure
class QualitativeEvaluationPart:
    question_key: str
    weight_percentage: int
    criteria: tuple[QualitativeCriterion, ...]

    def __post_init__(self) -> None:
        require_weight_total(
            (criterion.weight_percentage for criterion in self.criteria),
            InvalidEvaluationRuleError,
        )
