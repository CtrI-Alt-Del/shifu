from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import require_non_empty


@structure
class ChoiceOption:
    key: str
    text: str
    is_correct: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self, 'key', require_non_empty(self.key, InvalidActivityError)
        )
        object.__setattr__(
            self, 'text', require_non_empty(self.text, InvalidActivityError)
        )
