from shifu.communication.core.domain.enums import (
    CommunicationChannel,
    CommunicationType,
)
from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.communication.core.domain.structures.message_content import MessageContent
from shifu.communication.core.domain.structures.message_template_values import (
    MessageTemplateValues,
)
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import normalize_email, require_non_empty


@structure
class CommunicationRequest:
    communication_id: str
    identity_confirmation_id: str
    account_id: str | None
    type: CommunicationType
    channel: CommunicationChannel
    recipient_email: str
    recipient_name: str | None
    content: MessageContent | None = None
    message_values: MessageTemplateValues | None = None
    idempotency_key: str = ''

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            'communication_id',
            require_non_empty(self.communication_id, InvalidCommunicationError),
        )
        object.__setattr__(
            self,
            'identity_confirmation_id',
            require_non_empty(
                self.identity_confirmation_id,
                InvalidCommunicationError,
            ),
        )
        try:
            message_type = CommunicationType(self.type)
            channel = CommunicationChannel(self.channel)
        except ValueError:
            raise InvalidCommunicationError from None
        if channel is not CommunicationChannel.EMAIL:
            raise InvalidCommunicationError
        object.__setattr__(self, 'type', message_type)
        object.__setattr__(self, 'channel', channel)
        object.__setattr__(
            self,
            'recipient_email',
            normalize_email(self.recipient_email, InvalidCommunicationError),
        )
        if self.content is None and self.message_values is None:
            raise InvalidCommunicationError
        object.__setattr__(
            self,
            'idempotency_key',
            require_non_empty(
                self.idempotency_key or self.communication_id,
                InvalidCommunicationError,
            ),
        )
