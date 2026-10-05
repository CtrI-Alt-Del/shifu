from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import NonEmptyText, structure


@structure
class ChoiceOption:
    key: str
    text: str
    is_correct: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            'key',
            NonEmptyText.create(self.key, error_type=InvalidActivityError).value,
        )
        object.__setattr__(
            self,
            'text',
            NonEmptyText.create(self.text, error_type=InvalidActivityError).value,
        )
