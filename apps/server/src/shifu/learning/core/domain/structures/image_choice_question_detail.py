from typing import Literal

from shifu.learning.core.domain.structures.image_choice_option_detail import (
    ImageChoiceOptionDetail,
)
from shifu.shared.core.domain.structures import structure


@structure
class ImageChoiceQuestionDetail:
    key: str
    kind: Literal['image_choice']
    prompt: str
    options: tuple[ImageChoiceOptionDetail, ...]
