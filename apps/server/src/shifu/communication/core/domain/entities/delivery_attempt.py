from datetime import datetime

from shifu.communication.core.domain.enums import DeliveryAttemptStatus
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
