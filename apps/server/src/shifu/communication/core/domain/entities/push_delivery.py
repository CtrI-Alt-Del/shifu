from datetime import datetime

from shifu.communication.core.domain.enums import PushDeliveryStatus
from shifu.communication.core.domain.errors import (
    CommunicationTransitionError,
    InvalidCommunicationError,
)
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.structures import NonEmptyText


@entity
class PushDelivery:
    id: str
    reminder_id: str
    subscription_id: str
    status: PushDeliveryStatus
    attempted_at: datetime
    completed_at: datetime | None
    failure_code: str | None

    def __post_init__(self) -> None:
        NonEmptyText.create(self.id, error_type=InvalidCommunicationError)
        NonEmptyText.create(self.reminder_id, error_type=InvalidCommunicationError)
        NonEmptyText.create(self.subscription_id, error_type=InvalidCommunicationError)
        try:
            self.status = PushDeliveryStatus(self.status)
        except ValueError:
            raise InvalidCommunicationError from None

    @classmethod
    def create(
        cls,
        *,
        id: str,
        reminder_id: str,
        subscription_id: str,
        attempted_at: datetime,
    ) -> 'PushDelivery':
        return cls(
            id=id,
            reminder_id=reminder_id,
            subscription_id=subscription_id,
            status=PushDeliveryStatus.SENDING,
            attempted_at=attempted_at,
            completed_at=None,
            failure_code=None,
        )

    def mark_sent(self, completed_at: datetime) -> None:
        self._require_sending()
        self.status = PushDeliveryStatus.SENT
        self.completed_at = completed_at

    def mark_failed(self, completed_at: datetime, failure_code: str) -> None:
        self._require_sending()
        self.failure_code = NonEmptyText.create(
            failure_code, error_type=InvalidCommunicationError
        ).value
        self.status = PushDeliveryStatus.FAILED
        self.completed_at = completed_at

    def _require_sending(self) -> None:
        if self.status is not PushDeliveryStatus.SENDING:
            raise CommunicationTransitionError
