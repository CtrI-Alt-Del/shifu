from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import require_non_empty


@structure
class ChoiceOptionDetail:
    key: str
    text: str

    def __post_init__(self) -> None:
        object.__setattr__(self, 'key', require_non_empty(self.key, ValidationError))
        object.__setattr__(self, 'text', require_non_empty(self.text, ValidationError))
