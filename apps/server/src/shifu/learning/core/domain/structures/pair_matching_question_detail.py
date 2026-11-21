from typing import Literal

from shifu.learning.core.domain.structures.pair_matching_item_detail import (
    PairMatchingItemDetail,
)
from shifu.shared.core.domain.structures import structure


@structure
class PairMatchingQuestionDetail:
    key: str
    prompt: str
    source_language: str
    target_language: str
    words: tuple[PairMatchingItemDetail, ...]
    translations: tuple[PairMatchingItemDetail, ...]
    kind: Literal['pair_matching'] = 'pair_matching'
