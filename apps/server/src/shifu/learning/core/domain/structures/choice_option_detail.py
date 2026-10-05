from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import NonEmptyText, structure


@structure
class ChoiceOptionDetail:
    key: str
    text: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, 'key', NonEmptyText.create(self.key, error_type=ValidationError).value
        )
        object.__setattr__(
            self,
            'text',
            NonEmptyText.create(self.text, error_type=ValidationError).value,
        )
