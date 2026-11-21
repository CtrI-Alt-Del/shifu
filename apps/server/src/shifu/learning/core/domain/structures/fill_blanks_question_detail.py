from typing import Literal

from shifu.learning.core.domain.structures.fill_blanks_segment_detail import (
    FillBlanksSegmentDetail,
)
from shifu.learning.core.domain.structures.fill_blanks_word_detail import (
    FillBlanksWordDetail,
)
from shifu.shared.core.domain.structures import structure


@structure
class FillBlanksQuestionDetail:
    key: str
    prompt: str
    content_language: str
    segments: tuple[FillBlanksSegmentDetail, ...]
    bank: tuple[FillBlanksWordDetail, ...]
    kind: Literal['fill_blanks'] = 'fill_blanks'
