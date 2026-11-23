from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.structure import structure

PRACTICAL_PREPARATION_LEVEL_SCORES = (0, 25, 50, 75, 100)


@structure
class CurriculumPracticalPreparationLevelSnapshot:
    score: int
    description: str
    comment_key: str

    def __post_init__(self) -> None:
        for name in ('description', 'comment_key'):
            object.__setattr__(
                self,
                name,
                NonEmptyText.create(
                    getattr(self, name), error_type=ValidationError
                ).value,
            )
        if self.score not in PRACTICAL_PREPARATION_LEVEL_SCORES:
            raise ValidationError
