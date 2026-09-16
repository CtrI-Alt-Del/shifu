from dataclasses import field

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class AccountPasswordChangedPayload:
    account_id: str
    access_version: int
    changed_at: str


@structure
class AccountPasswordChangedEvent(Event[AccountPasswordChangedPayload]):
    name: str = field(default='identity/account.password-changed', init=False)
