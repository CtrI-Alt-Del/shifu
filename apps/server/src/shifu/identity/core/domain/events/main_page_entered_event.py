from dataclasses import field

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class MainPageEnteredPayload:
    event_id: str
    account_id: str
    occurred_at: str


@structure
class MainPageEnteredEvent(Event[MainPageEnteredPayload]):
    name: str = field(default='app/main-page.entered', init=False)
