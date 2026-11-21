from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import NonEmptyText, structure


@structure
class PairMatchingItem:
    key: str
    text: str

    def __post_init__(self) -> None:
        NonEmptyText.create(self.key, error_type=InvalidActivityError)
        NonEmptyText.create(self.text, error_type=InvalidActivityError)
