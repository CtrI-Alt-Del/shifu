from decimal import Decimal
from typing import Literal

from shifu.learning.core.domain.structures.pair_matching_selection import (
    PairMatchingSelection,
)
from shifu.shared.core.domain.structures import structure


@structure
class PairMatchingResultDetail:
    question_key: str
    kind: Literal['pair_matching']
    prompt: str
    submitted_pairs: tuple[PairMatchingSelection, ...]
    score: Decimal
    correct_pair_count: int
    total_pair_count: int
    outcome: Literal['full', 'partial', 'incorrect']
    explanation: str
    disclosed_correct_pairs: tuple[PairMatchingSelection, ...] = ()
