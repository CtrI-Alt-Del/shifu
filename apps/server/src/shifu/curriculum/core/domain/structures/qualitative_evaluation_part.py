from shifu.shared.core.domain.structures import WeightDistribution, structure
from shifu.curriculum.core.domain.errors import InvalidEvaluationRuleError

from .qualitative_criterion import QualitativeCriterion


@structure
class QualitativeEvaluationPart:
    question_key: str
    weight_percentage: int
    criteria: tuple[QualitativeCriterion, ...]

    def __post_init__(self) -> None:
        WeightDistribution.create(
            (criterion.weight_percentage for criterion in self.criteria),
            error_type=InvalidEvaluationRuleError,
        )
