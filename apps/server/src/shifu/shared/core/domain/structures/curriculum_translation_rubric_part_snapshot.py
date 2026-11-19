from decimal import Decimal

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.percentage import Percentage
from shifu.shared.core.domain.structures.structure import structure

from .curriculum_translation_rubric_criterion_snapshot import (
    CurriculumTranslationRubricCriterionSnapshot,
)

_REQUIRED_CRITERIA_WEIGHTS = {
    'semantic_preservation': 70,
    'grammatical_adequacy': 30,
}


@structure
class CurriculumTranslationRubricPartSnapshot:
    question_key: str
    weight_percentage: Decimal
    criteria: tuple[CurriculumTranslationRubricCriterionSnapshot, ...]

    def __post_init__(self) -> None:
        NonEmptyText.create(self.question_key, error_type=ValidationError)
        Percentage.create(self.weight_percentage, error_type=ValidationError)
        criteria_by_key = {criterion.key: criterion for criterion in self.criteria}
        if (
            len(self.criteria) != 2
            or set(criteria_by_key) != set(_REQUIRED_CRITERIA_WEIGHTS)
            or any(not criterion.required for criterion in self.criteria)
            or any(
                criteria_by_key[key].weight_percentage != weight
                for key, weight in _REQUIRED_CRITERIA_WEIGHTS.items()
            )
        ):
            raise ValidationError
