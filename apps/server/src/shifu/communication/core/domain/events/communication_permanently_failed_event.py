from dataclasses import field

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class CommunicationPermanentlyFailedPayload:
    communication_id: str
    account_id: str | None
    failure_code: str
    failed_at: str


@structure
class CommunicationPermanentlyFailedEvent(Event[CommunicationPermanentlyFailedPayload]):
    name: str = field(
        default='communication/communication.permanently-failed', init=False
    )
