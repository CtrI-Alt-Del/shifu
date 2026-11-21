from typing import Literal

from shifu.learning.core.domain.structures.fill_blanks_placement import (
    FillBlanksPlacement,
)
from shifu.shared.core.domain.structures import structure


@structure
class FillBlanksAnswer:
    question_key: str
    placements: tuple[FillBlanksPlacement, ...]
    kind: Literal['fill_blanks'] = 'fill_blanks'
