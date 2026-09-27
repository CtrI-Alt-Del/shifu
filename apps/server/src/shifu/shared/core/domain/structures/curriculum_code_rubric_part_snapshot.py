from decimal import Decimal

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.structure import structure
from shifu.shared.core.domain.validation import require_non_empty, require_percentage

from .curriculum_code_rubric_criterion_snapshot import (
    CurriculumCodeRubricCriterionSnapshot,
)


@structure
class CurriculumCodeRubricPartSnapshot:
    question_key: str
    weight_percentage: Decimal
    criteria: tuple[CurriculumCodeRubricCriterionSnapshot, ...]

    def __post_init__(self) -> None:
        require_non_empty(self.question_key, ValidationError)
        require_percentage(self.weight_percentage, ValidationError)
        if (
            not self.criteria
            or sum(item.weight_percentage for item in self.criteria) != 100
            or len(self.criteria) != len({item.key for item in self.criteria})
            or not any(item.required for item in self.criteria)
        ):
            raise ValidationError
