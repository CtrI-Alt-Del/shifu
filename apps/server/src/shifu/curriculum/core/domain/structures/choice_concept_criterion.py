from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import require_non_empty


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
                self, name, require_non_empty(getattr(self, name), InvalidActivityError)
            )
        for score in (self.correct_score, self.incorrect_score):
            if score is not None and not 0 <= score <= 100:
                raise InvalidActivityError
