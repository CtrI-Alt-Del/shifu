from decimal import Decimal

from shifu.learning.core.domain.structures.ordering_question_detail import (
    OrderingStepDetail,
)
from shifu.shared.core.domain.structures import structure


@structure
class OrderingResultDetail:
    question_key: str
    kind: str
    prompt: str
    steps: tuple[OrderingStepDetail, ...]
    submitted_step_keys: tuple[str, ...]
    score: Decimal
    is_correct: bool
    explanation: str
    accepted_orders: tuple[tuple[str, ...], ...] = ()
