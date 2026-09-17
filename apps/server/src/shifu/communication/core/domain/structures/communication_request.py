from shifu.communication.core.domain.enums import (
    CommunicationChannel,
    CommunicationType,
)
from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.communication.core.domain.structures.message_content import MessageContent
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import normalize_email, require_non_empty


@structure
class CommunicationRequest:
    account_id: str | None
    type: CommunicationType
    channel: CommunicationChannel
    recipient_email: str
    recipient_name: str | None
    content: MessageContent
    idempotency_key: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            'recipient_email',
            normalize_email(self.recipient_email, InvalidCommunicationError),
        )
        object.__setattr__(
            self,
            'idempotency_key',
            require_non_empty(self.idempotency_key, InvalidCommunicationError),
        )
