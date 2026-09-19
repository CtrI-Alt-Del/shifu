from dataclasses import field

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class AccountDeletedPayload:
    account_id: str
    deleted_at: str


@structure
class AccountDeletedEvent(Event[AccountDeletedPayload]):
    name: str = field(default='identity/account.deleted', init=False)
