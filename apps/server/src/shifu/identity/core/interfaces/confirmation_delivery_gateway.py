from datetime import datetime
from typing import Protocol

from shifu.identity.core.domain.enums import ConfirmationDeliveryQueueStatus
from shifu.shared.core.domain.structures import structure


@structure
class ConfirmationDeliveryRequest:
    """The minimum in-process data needed to queue one confirmation message."""

    communication_id: str
    identity_confirmation_id: str
    account_id: str
    recipient_email: str
    recipient_name: str
    confirmation_token: str
    expires_at: datetime


@structure
class ConfirmationDeliveryResult:
    status: ConfirmationDeliveryQueueStatus


class ConfirmationDeliveryGateway(Protocol):
    def queue(
        self,
        request: ConfirmationDeliveryRequest,
    ) -> ConfirmationDeliveryResult: ...
