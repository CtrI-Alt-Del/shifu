from decimal import Decimal
from typing import Literal

from shifu.learning.core.domain.structures.image_choice_option_detail import (
    ImageChoiceOptionDetail,
)
from shifu.shared.core.domain.structures import structure


@structure
class ImageChoiceResultDetail:
    question_key: str
    kind: Literal['image_choice']
    prompt: str
    options: tuple[ImageChoiceOptionDetail, ...]
    selected_option_key: str
    score: Decimal
    is_correct: bool
    option_feedback: str
    explanation: str
    disclosed_correct_option_key: str | None = None
