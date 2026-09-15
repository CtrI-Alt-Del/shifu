from typing import Protocol

from shifu.communication.core.domain.structures import (
    DeliveryOutcome,
    EmailMessage,
)


class EmailDeliveryProvider(Protocol):
    def send(self, message: EmailMessage) -> DeliveryOutcome: ...
