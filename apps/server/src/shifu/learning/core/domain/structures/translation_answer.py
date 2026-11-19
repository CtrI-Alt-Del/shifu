from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText


@structure
class TranslationAnswer:
    question_key: str
    text: str

    def __post_init__(self) -> None:
        normalized = NonEmptyText.create(self.text, error_type=ValidationError)
        object.__setattr__(self, 'text', normalized.value)
