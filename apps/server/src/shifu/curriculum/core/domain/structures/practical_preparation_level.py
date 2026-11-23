from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import NonEmptyText, structure

PRACTICE_LEVEL_SCORES = (0, 25, 50, 75, 100)


@structure
class PracticeCriterionLevel:
    score: int
    description: str
    comment_key: str

    def __post_init__(self) -> None:
        for name in ('description', 'comment_key'):
            object.__setattr__(
                self,
                name,
                NonEmptyText.create(
                    getattr(self, name), error_type=InvalidActivityError
                ).value,
            )
        if self.score not in PRACTICE_LEVEL_SCORES:
            raise InvalidActivityError
