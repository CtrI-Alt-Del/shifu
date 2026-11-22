from datetime import datetime

from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.structures import NonEmptyText


@entity
class StreakReminderPreference:
    id: str
    enabled: bool
    updated_at: datetime

    def __post_init__(self) -> None:
        NonEmptyText.create(self.id, error_type=InvalidCommunicationError)

    @classmethod
    def create(
        cls,
        *,
        account_id: str,
        enabled: bool,
        now: datetime,
    ) -> 'StreakReminderPreference':
        return cls(id=account_id, enabled=enabled, updated_at=now)

    @property
    def account_id(self) -> str:
        return self.id

    def change(self, *, enabled: bool, now: datetime) -> None:
        self.enabled = enabled
        self.updated_at = now
