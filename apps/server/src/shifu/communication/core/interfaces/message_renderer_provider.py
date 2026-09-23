from typing import Protocol

from shifu.communication.core.domain.enums import CommunicationType
from shifu.communication.core.domain.structures import (
    EmailMessage,
    MessageContent,
    MessageTemplateValues,
)


class MessageRendererProvider(Protocol):
    def render(
        self,
        message_type: CommunicationType,
        values: MessageContent | MessageTemplateValues,
    ) -> EmailMessage: ...
