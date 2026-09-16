from dataclasses import field

from shifu.identity.core.domain.enums import AccountStatus
from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class AccountCreatedPayload:
    account_id: str
    status: AccountStatus
    created_at: str


@structure
class AccountCreatedEvent(Event[AccountCreatedPayload]):
    name: str = field(default='identity/account.created', init=False)
