from dataclasses import field
from typing import ClassVar

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class CommunicationQueuedPayload:
    communication_id: str


@structure
class CommunicationQueuedEvent(Event[CommunicationQueuedPayload]):
    EVENT_NAME: ClassVar[str] = 'communication/communication.queued'
    name: str = field(default=EVENT_NAME, init=False)
