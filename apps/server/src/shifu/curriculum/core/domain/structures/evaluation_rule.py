from shifu.shared.core.domain.structures import WeightDistribution, structure
from shifu.curriculum.core.domain.errors import InvalidEvaluationRuleError

from .evaluation_part import EvaluationPart


@structure
class EvaluationRule:
    parts: tuple[EvaluationPart, ...]

    def __post_init__(self) -> None:
        WeightDistribution.create(
            (part.weight_percentage for part in self.parts),
            error_type=InvalidEvaluationRuleError,
        )
