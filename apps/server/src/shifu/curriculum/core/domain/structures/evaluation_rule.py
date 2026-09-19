from shifu.shared.core.domain.structures import structure
from shifu.curriculum.core.domain.errors import InvalidEvaluationRuleError
from shifu.shared.core.domain.validation import require_weight_total

from .evaluation_part import EvaluationPart


@structure
class EvaluationRule:
    parts: tuple[EvaluationPart, ...]

    def __post_init__(self) -> None:
        require_weight_total(
            (part.weight_percentage for part in self.parts),
            InvalidEvaluationRuleError,
        )
