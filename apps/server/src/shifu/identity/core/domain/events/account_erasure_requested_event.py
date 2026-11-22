from dataclasses import field
from typing import ClassVar

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class AccountErasureRequestedPayload:
    erasure_id: str


@structure
class AccountErasureRequestedEvent(Event[AccountErasureRequestedPayload]):
    EVENT_NAME: ClassVar[str] = 'identity/account-erasure.requested'
    name: str = field(default=EVENT_NAME, init=False)
