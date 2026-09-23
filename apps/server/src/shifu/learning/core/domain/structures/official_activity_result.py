from datetime import datetime
from decimal import Decimal

from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import require_percentage


@structure
class OfficialActivityResult:
    activity_id: str
    attempt_id: str
    score: Decimal
    submitted_at: datetime
    completed_at: datetime

    def __post_init__(self) -> None:
        require_percentage(self.score, InvalidAttemptError)
        if self.completed_at < self.submitted_at:
            raise InvalidAttemptError
