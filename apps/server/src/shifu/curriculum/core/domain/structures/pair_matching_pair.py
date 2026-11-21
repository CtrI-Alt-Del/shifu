from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import NonEmptyText, structure


@structure
class PairMatchingPair:
    word_key: str
    translation_key: str

    def __post_init__(self) -> None:
        NonEmptyText.create(self.word_key, error_type=InvalidActivityError)
        NonEmptyText.create(self.translation_key, error_type=InvalidActivityError)
