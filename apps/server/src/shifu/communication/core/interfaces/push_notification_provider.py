from typing import Protocol

from shifu.communication.core.domain.entities import PushSubscription
from shifu.communication.core.domain.structures import (
    PushDeliveryOutcome,
    StreakReminderMessage,
)


class PushNotificationProvider(Protocol):
    @property
    def public_key(self) -> str: ...

    def send(
        self,
        message: StreakReminderMessage,
        subscription: PushSubscription,
        *,
        ttl_seconds: int,
    ) -> PushDeliveryOutcome: ...
