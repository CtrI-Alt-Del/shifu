from dataclasses import field

from shifu.communication.core.domain.enums import CommunicationDeliveryState
from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import require_non_empty


@structure
class CommunicationDeliveryStateChangedPayload:
    communication_id: str
    identity_confirmation_id: str
    state: CommunicationDeliveryState | str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            'communication_id',
            require_non_empty(self.communication_id, InvalidCommunicationError),
        )
        object.__setattr__(
            self,
            'identity_confirmation_id',
            require_non_empty(
                self.identity_confirmation_id,
                InvalidCommunicationError,
            ),
        )
        try:
            state = CommunicationDeliveryState(self.state)
        except ValueError:
            raise InvalidCommunicationError from None
        object.__setattr__(self, 'state', state)


@structure
class CommunicationDeliveryStateChangedEvent(
    Event[CommunicationDeliveryStateChangedPayload]
):
    name: str = field(default='communication.delivery-state-changed', init=False)


CommunicationDeliveryStateChanged = CommunicationDeliveryStateChangedEvent
