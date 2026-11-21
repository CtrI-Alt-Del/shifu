from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText


@structure
class PairMatchingSelection:
    word_key: str
    translation_key: str

    def __post_init__(self) -> None:
        NonEmptyText.create(self.word_key, error_type=ValidationError)
        NonEmptyText.create(self.translation_key, error_type=ValidationError)
