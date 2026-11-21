from shifu.learning.core.domain.structures.pair_matching_selection import (
    PairMatchingSelection,
)
from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import structure


@structure
class PairMatchingAnswer:
    question_key: str
    pairs: tuple[PairMatchingSelection, ...]

    def __post_init__(self) -> None:
        if (
            not self.question_key
            or not self.pairs
            or len({pair.word_key for pair in self.pairs}) != len(self.pairs)
            or len({pair.translation_key for pair in self.pairs}) != len(self.pairs)
        ):
            raise ValidationError
