from dataclasses import field

from shifu.communication.core.domain.enums import CommunicationDeliveryState
from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import NonEmptyText, structure


@structure
class CommunicationDeliveryStateChangedPayload:
    communication_id: str
    identity_action_token_id: str
    state: CommunicationDeliveryState | str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            'communication_id',
            NonEmptyText.create(
                self.communication_id, error_type=InvalidCommunicationError
            ).value,
        )
        object.__setattr__(
            self,
            'identity_action_token_id',
            NonEmptyText.create(
                self.identity_action_token_id, error_type=InvalidCommunicationError
            ).value,
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
