from shifu.shared.core.domain.structures import structure

from .qualitative_criterion import QualitativeCriterion


@structure
class QualitativeEvaluationPart:
    question_key: str
    weight_percentage: int
    criteria: tuple[QualitativeCriterion, ...]
