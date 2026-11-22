from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import NonEmptyText, structure


@structure
class PairMatchingConceptCriterion:
    concept_id: str
    criterion: str
    examples: str
    limits: str
    full_score: int | None
    partial_score: int | None
    incorrect_score: int | None

    def __post_init__(self) -> None:
        for name in ('concept_id', 'criterion', 'examples', 'limits'):
            NonEmptyText.create(getattr(self, name), error_type=InvalidActivityError)

        for score in (self.full_score, self.partial_score, self.incorrect_score):
            if score is not None and not 0 <= score <= 100:
                raise InvalidActivityError
