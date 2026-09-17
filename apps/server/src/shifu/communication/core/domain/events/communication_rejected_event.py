from dataclasses import field

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class CommunicationRejectedPayload:
    communication_id: str
    account_id: str | None
    rejection_code: str
    rejected_at: str


@structure
class CommunicationRejectedEvent(Event[CommunicationRejectedPayload]):
    name: str = field(default='communication/communication.rejected', init=False)
