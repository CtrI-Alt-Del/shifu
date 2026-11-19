from decimal import Decimal
from typing import Literal

from shifu.shared.core.domain.structures import structure


@structure
class OrderingStepDetail:
    key: str
    text: str


@structure
class VerifiedOrderingDetail:
    ordered_step_keys: tuple[str, ...]
    score: Decimal
    is_correct: bool
    explanation: str


@structure
class OrderingQuestionDetail:
    key: str
    kind: Literal['ordering']
    prompt: str
    steps: tuple[OrderingStepDetail, ...]
    initial_ordered_step_keys: tuple[str, ...]
    verified: VerifiedOrderingDetail | None = None
