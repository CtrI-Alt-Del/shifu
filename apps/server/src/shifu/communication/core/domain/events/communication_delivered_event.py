from dataclasses import field

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class CommunicationDeliveredPayload:
    communication_id: str
    account_id: str | None
    provider_message_id: str | None
    delivered_at: str


@structure
class CommunicationDeliveredEvent(Event[CommunicationDeliveredPayload]):
    name: str = field(default='communication/communication.delivered', init=False)
