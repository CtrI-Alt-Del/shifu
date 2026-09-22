from decimal import Decimal

from shifu.learning.core.domain.enums import ActivityDifficulty
from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import require_percentage


@structure
class CompetencyActivityDetail:
    id: str
    title: str
    position: int
    activity_type: str
    difficulty: ActivityDifficulty
    latest_score: Decimal | None

    def __post_init__(self) -> None:
        if self.position < 1:
            raise ValueError('Competency content positions must be positive.')
        if self.latest_score is not None:
            require_percentage(self.latest_score, InvalidAttemptError)
