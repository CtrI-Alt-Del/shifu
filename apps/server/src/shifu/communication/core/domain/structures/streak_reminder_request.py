from datetime import date, datetime

from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.shared.core.domain.structures import NonEmptyText, structure


@structure
class StreakReminderRequest:
    account_id: str
    local_date: date
    streak_days: int
    expires_at: datetime

    def __post_init__(self) -> None:
        NonEmptyText.create(self.account_id, error_type=InvalidCommunicationError)
        if type(self.local_date) is not date or self.streak_days < 1:
            raise InvalidCommunicationError
        if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
            raise InvalidCommunicationError
