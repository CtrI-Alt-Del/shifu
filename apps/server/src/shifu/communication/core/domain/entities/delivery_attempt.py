from datetime import datetime

from shifu.communication.core.domain.enums import DeliveryAttemptStatus
from shifu.communication.core.domain.errors import (
    CommunicationTransitionError,
    InvalidCommunicationError,
)
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.validation import require_non_empty


@entity
class DeliveryAttempt:
    id: str
    communication_id: str
    attempt_number: int
    status: DeliveryAttemptStatus
    attempted_at: datetime
    completed_at: datetime | None = None
    provider_message_id: str | None = None
    failure_code: str | None = None

    def __post_init__(self) -> None:
        require_non_empty(self.id, InvalidCommunicationError)
        require_non_empty(
            self.communication_id,
            InvalidCommunicationError,
        )
        if self.attempt_number < 1:
            raise InvalidCommunicationError
        try:
            self.status = DeliveryAttemptStatus(self.status)
        except ValueError:
            raise InvalidCommunicationError from None

    @classmethod
    def create(
        cls,
        *,
        id: str,
        communication_id: str,
        attempt_number: int,
        attempted_at: datetime,
    ) -> 'DeliveryAttempt':
        return cls(
            id=id,
            communication_id=communication_id,
            attempt_number=attempt_number,
            status=DeliveryAttemptStatus.STARTED,
            attempted_at=attempted_at,
        )

    def start(self, attempted_at: datetime) -> None:
        if self.status is not DeliveryAttemptStatus.STARTED:
            raise CommunicationTransitionError
        self.attempted_at = attempted_at

    def succeed(
        self,
        completed_at: datetime,
        provider_message_id: str | None,
    ) -> None:
        if self.status is not DeliveryAttemptStatus.STARTED:
            raise CommunicationTransitionError
        self.status = DeliveryAttemptStatus.SUCCEEDED
        self.completed_at = completed_at
        self.provider_message_id = provider_message_id

    def fail(self, completed_at: datetime, failure_code: str) -> None:
        if self.status is not DeliveryAttemptStatus.STARTED:
            raise CommunicationTransitionError
        self.status = DeliveryAttemptStatus.FAILED
        self.completed_at = completed_at
        self.failure_code = require_non_empty(
            failure_code,
            InvalidCommunicationError,
        )
