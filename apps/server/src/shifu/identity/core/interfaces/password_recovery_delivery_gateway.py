from datetime import datetime
from typing import Protocol

from shifu.identity.core.domain.enums import ActionTokenDeliveryQueueStatus
from shifu.shared.core.domain.structures import structure


@structure
class PasswordRecoveryDeliveryRequest:
    communication_id: str
    identity_action_token_id: str
    account_id: str
    recipient_email: str
    recovery_token: str
    expires_at: datetime


@structure
class PasswordRecoveryDeliveryResult:
    status: ActionTokenDeliveryQueueStatus


class PasswordRecoveryDeliveryGateway(Protocol):
    def queue(
        self,
        request: PasswordRecoveryDeliveryRequest,
    ) -> PasswordRecoveryDeliveryResult: ...
