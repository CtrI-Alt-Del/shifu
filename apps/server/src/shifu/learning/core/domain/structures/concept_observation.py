from datetime import datetime
from decimal import Decimal

from shifu.learning.core.domain.enums import ActivityDifficulty
from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import require_percentage


@structure
class ConceptObservation:
    attempt_id: str
    activity_id: str
    concept_id: str
    difficulty: ActivityDifficulty
    first_submitted_at: datetime
    submitted_at: datetime
    completed_at: datetime
    question_scores: tuple[Decimal | None, ...]
    diagnostic: bool = False

    def __post_init__(self) -> None:
        if (
            not self.question_scores
            or self.first_submitted_at > self.submitted_at
            or self.submitted_at > self.completed_at
        ):
            raise InvalidAttemptError
        for score in self.question_scores:
            if score is not None:
                require_percentage(score, InvalidAttemptError)

    @property
    def value(self) -> Decimal | None:
        if any(score is None for score in self.question_scores):
            return None
        return sum(
            (score for score in self.question_scores if score is not None),
            Decimal('0'),
        ) / Decimal(len(self.question_scores))
