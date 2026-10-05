from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import NonEmptyText, structure


@structure
class ChoiceConceptCriterion:
    concept_id: str
    criterion: str
    examples: str
    limits: str
    correct_score: int | None
    incorrect_score: int | None

    def __post_init__(self) -> None:
        for name in ('concept_id', 'criterion', 'examples', 'limits'):
            object.__setattr__(
                self,
                name,
                NonEmptyText.create(
                    getattr(self, name), error_type=InvalidActivityError
                ).value,
            )
        for score in (self.correct_score, self.incorrect_score):
            if score is not None and not 0 <= score <= 100:
                raise InvalidActivityError
