from datetime import datetime

from shifu.communication.core.domain.enums import DeliveryAttemptStatus
from shifu.communication.core.domain.errors import CommunicationTransitionError
from shifu.shared.core.domain.entities import entity


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

    def start(self, attempted_at: datetime) -> None:
        if self.status is not DeliveryAttemptStatus.STARTED:
            raise CommunicationTransitionError
        self.attempted_at = attempted_at

    def succeed(self, completed_at: datetime, provider_message_id: str) -> None:
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
        self.failure_code = failure_code
