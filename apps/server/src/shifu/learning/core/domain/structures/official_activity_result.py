from datetime import datetime
from decimal import Decimal

from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.shared.core.domain.structures import Percentage, structure


@structure
class OfficialActivityResult:
    activity_id: str
    attempt_id: str
    score: Decimal
    submitted_at: datetime
    completed_at: datetime

    def __post_init__(self) -> None:
        Percentage.create(self.score, error_type=InvalidAttemptError)
        if self.completed_at < self.submitted_at:
            raise InvalidAttemptError
