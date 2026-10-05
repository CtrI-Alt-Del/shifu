from decimal import Decimal

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.percentage import Percentage
from shifu.shared.core.domain.structures.structure import structure

from .curriculum_code_rubric_criterion_snapshot import (
    CurriculumCodeRubricCriterionSnapshot,
)


@structure
class CurriculumCodeRubricPartSnapshot:
    question_key: str
    weight_percentage: Decimal
    criteria: tuple[CurriculumCodeRubricCriterionSnapshot, ...]

    def __post_init__(self) -> None:
        NonEmptyText.create(self.question_key, error_type=ValidationError)
        Percentage.create(self.weight_percentage, error_type=ValidationError)
        if (
            not self.criteria
            or sum(item.weight_percentage for item in self.criteria) != 100
            or len(self.criteria) != len({item.key for item in self.criteria})
            or not any(item.required for item in self.criteria)
        ):
            raise ValidationError
