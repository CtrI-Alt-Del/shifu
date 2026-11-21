from decimal import Decimal

from shifu.shared.core.domain.structures import structure


@structure
class VerifiedOrdering:
    question_key: str
    ordered_step_keys: tuple[str, ...]
    score: Decimal
    is_correct: bool
    explanation: str
