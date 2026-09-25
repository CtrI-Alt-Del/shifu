from dataclasses import field

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class CommunicationQueuedPayload:
    communication_id: str


@structure
class CommunicationQueuedEvent(Event[CommunicationQueuedPayload]):
    name: str = field(default='communication/communication.queued', init=False)
