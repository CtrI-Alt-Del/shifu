from typing import Protocol

from shifu.communication.core.domain.structures import (
    MessageContent,
    MessageTemplateValues,
    SecretEnvelope,
)


class SecretEnvelopeProvider(Protocol):
    def encrypt(
        self,
        values: MessageContent | MessageTemplateValues,
    ) -> SecretEnvelope: ...

    def decrypt(
        self,
        envelope: SecretEnvelope,
    ) -> MessageContent | MessageTemplateValues: ...
