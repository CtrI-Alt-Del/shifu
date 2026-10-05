from decimal import Decimal

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.percentage import Percentage


@structure
class CurriculumChoicePartSnapshot:
    question_key: str
    weight_percentage: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            'question_key',
            NonEmptyText.create(self.question_key, error_type=ValidationError).value,
        )
        Percentage.create(self.weight_percentage, error_type=ValidationError)
