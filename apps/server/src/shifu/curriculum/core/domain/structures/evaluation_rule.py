from shifu.shared.core.domain.structures import structure

from .evaluation_part import EvaluationPart


@structure
class EvaluationRule:
    parts: tuple[EvaluationPart, ...]
