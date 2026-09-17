from dataclasses import field

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class AccountExpiredPayload:
    account_id: str
    expired_at: str


@structure
class AccountExpiredEvent(Event[AccountExpiredPayload]):
    name: str = field(default='identity/account.expired', init=False)
