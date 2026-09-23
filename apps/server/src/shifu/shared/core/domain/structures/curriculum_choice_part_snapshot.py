from decimal import Decimal

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import require_non_empty, require_percentage


@structure
class CurriculumChoicePartSnapshot:
    question_key: str
    weight_percentage: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(
            self, 'question_key', require_non_empty(self.question_key, ValidationError)
        )
        require_percentage(self.weight_percentage, ValidationError)
