from datetime import datetime

from shifu.communication.core.domain.enums import (
    CommunicationChannel,
    CommunicationStatus,
    CommunicationType,
)
from shifu.communication.core.domain.structures import MessageContent
from shifu.shared.core.domain.entities import entity


@entity
class Communication:
    id: str
    account_id: str | None
    type: CommunicationType
    channel: CommunicationChannel
    recipient_email: str
    recipient_name: str | None
    content: MessageContent
    status: CommunicationStatus
    idempotency_key: str
    created_at: datetime
    updated_at: datetime
    sent_at: datetime | None = None
    failed_at: datetime | None = None
    failure_code: str | None = None
    provider_message_id: str | None = None
    attempt_count: int = 0
    next_attempt_at: datetime | None = None


Message = Communication
