from decimal import Decimal

from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import NonEmptyText, structure

from .practical_preparation_level import PRACTICE_LEVEL_SCORES, PracticeCriterionLevel


@structure
class PracticeCriterion:
    key: str
    name: str
    description: str
    weight: Decimal
    levels: tuple[PracticeCriterionLevel, ...]
    inconclusive_when: str

    def __post_init__(self) -> None:
        for name in ('key', 'name', 'description', 'inconclusive_when'):
            object.__setattr__(
                self,
                name,
                NonEmptyText.create(
                    getattr(self, name), error_type=InvalidActivityError
                ).value,
            )
        if (
            not self.weight.is_finite()
            or not Decimal(0) < self.weight <= Decimal(100)
            or tuple(sorted(level.score for level in self.levels))
            != PRACTICE_LEVEL_SCORES
            or len({level.comment_key for level in self.levels}) != len(self.levels)
        ):
            raise InvalidActivityError
