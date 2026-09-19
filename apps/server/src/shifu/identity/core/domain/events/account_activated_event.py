from dataclasses import field

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class AccountActivatedPayload:
    account_id: str
    activated_at: str


@structure
class AccountActivatedEvent(Event[AccountActivatedPayload]):
    name: str = field(default='identity/account.activated', init=False)
