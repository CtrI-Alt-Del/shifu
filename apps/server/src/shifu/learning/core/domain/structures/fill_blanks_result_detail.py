from decimal import Decimal
from typing import Literal

from shifu.learning.core.domain.structures.fill_blanks_expected_blank import (
    FillBlanksExpectedBlank,
)
from shifu.learning.core.domain.structures.fill_blanks_placement import (
    FillBlanksPlacement,
)
from shifu.learning.core.domain.structures.fill_blanks_segment_detail import (
    FillBlanksSegmentDetail,
)
from shifu.learning.core.domain.structures.fill_blanks_word_detail import (
    FillBlanksWordDetail,
)
from shifu.shared.core.domain.structures import structure


@structure
class FillBlanksResultDetail:
    question_key: str
    prompt: str
    content_language: str
    segments: tuple[FillBlanksSegmentDetail, ...]
    bank: tuple[FillBlanksWordDetail, ...]
    placements: tuple[FillBlanksPlacement, ...]
    score: Decimal
    is_correct: bool
    correct_blank_count: int
    blank_count: int
    explanation: str
    disclosed_expected_blanks: tuple[FillBlanksExpectedBlank, ...] = ()
    kind: Literal['fill_blanks'] = 'fill_blanks'
