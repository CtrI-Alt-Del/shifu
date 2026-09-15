from dataclasses import field

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class AccountDeletionRequestedPayload:
    account_id: str
    requested_at: str


@structure
class AccountDeletionRequestedEvent(Event[AccountDeletionRequestedPayload]):
    name: str = field(default='identity/account-deletion.requested', init=False)
