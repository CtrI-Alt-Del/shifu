from decimal import Decimal

from shifu.learning.core.domain.enums import ActivityDifficulty
from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.learning.core.domain.structures.competency_content_concept import (
    CompetencyContentConcept,
)
from shifu.shared.core.domain.structures import Percentage, structure


@structure
class CompetencyActivityDetail:
    id: str
    title: str
    position: int
    activity_type: str
    difficulty: ActivityDifficulty
    latest_score: Decimal | None
    concepts: tuple[CompetencyContentConcept, ...] = ()

    def __post_init__(self) -> None:
        if self.position < 1:
            raise ValueError('Competency content positions must be positive.')

        if self.latest_score is not None:
            Percentage.create(self.latest_score, error_type=InvalidAttemptError)
