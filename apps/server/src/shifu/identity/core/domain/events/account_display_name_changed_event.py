from dataclasses import field

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class AccountDisplayNameChangedPayload:
    account_id: str
    display_name: str
    updated_at: str


@structure
class AccountDisplayNameChangedEvent(Event[AccountDisplayNameChangedPayload]):
    name: str = field(default='identity/account.display-name-changed', init=False)
