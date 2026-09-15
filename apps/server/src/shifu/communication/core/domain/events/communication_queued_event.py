from dataclasses import field

from shifu.communication.core.domain.enums import CommunicationType
from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class CommunicationQueuedPayload:
    communication_id: str
    account_id: str | None
    type: CommunicationType
    queued_at: str


@structure
class CommunicationQueuedEvent(Event[CommunicationQueuedPayload]):
    name: str = field(default='communication/communication.queued', init=False)
