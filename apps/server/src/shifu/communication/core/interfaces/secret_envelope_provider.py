from typing import Protocol

from shifu.communication.core.domain.structures import (
    MessageContent,
    AccountErasureOperationalAlertValues,
    MessageTemplateValues,
    SecretEnvelope,
)


class SecretEnvelopeProvider(Protocol):
    def encrypt(
        self,
        values: MessageContent
        | MessageTemplateValues
        | AccountErasureOperationalAlertValues,
    ) -> SecretEnvelope: ...

    def decrypt(
        self,
        envelope: SecretEnvelope,
    ) -> (
        MessageContent | MessageTemplateValues | AccountErasureOperationalAlertValues
    ): ...
