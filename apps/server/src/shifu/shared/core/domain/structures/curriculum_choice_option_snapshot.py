from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText


@structure
class CurriculumChoiceOptionSnapshot:
    key: str
    text: str
    is_correct: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self, 'key', NonEmptyText.create(self.key, error_type=ValidationError).value
        )
        object.__setattr__(
            self,
            'text',
            NonEmptyText.create(self.text, error_type=ValidationError).value,
        )
