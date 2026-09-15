from decimal import Decimal

from shifu.shared.core.domain.structures import structure


@structure
class ChoiceEvaluationResult:
    question_key: str
    score: Decimal
    is_correct: bool
    explanation: str
