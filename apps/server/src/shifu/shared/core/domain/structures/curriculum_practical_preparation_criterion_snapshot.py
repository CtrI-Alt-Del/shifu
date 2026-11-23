from decimal import Decimal

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.curriculum_practical_preparation_level_snapshot import (
    PRACTICAL_PREPARATION_LEVEL_SCORES,
    CurriculumPracticalPreparationLevelSnapshot,
)
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.structure import structure


@structure
class CurriculumPracticalPreparationCriterionSnapshot:
    key: str
    name: str
    description: str
    weight: Decimal
    levels: tuple[CurriculumPracticalPreparationLevelSnapshot, ...]
    inconclusive_when: str

    def __post_init__(self) -> None:
        for name in ('key', 'name', 'description', 'inconclusive_when'):
            object.__setattr__(
                self,
                name,
                NonEmptyText.create(
                    getattr(self, name), error_type=ValidationError
                ).value,
            )
        if (
            not self.weight.is_finite()
            or not Decimal(0) < self.weight <= Decimal(100)
            or tuple(sorted(level.score for level in self.levels))
            != PRACTICAL_PREPARATION_LEVEL_SCORES
            or len({level.comment_key for level in self.levels}) != len(self.levels)
        ):
            raise ValidationError
