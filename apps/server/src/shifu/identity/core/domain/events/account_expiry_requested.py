from dataclasses import field

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class AccountExpiryRequestedPayload:
    account_id: str


@structure
class AccountExpiryRequestedEvent(Event[AccountExpiryRequestedPayload]):
    name: str = field(default='identity.account-expiry-requested', init=False)


AccountExpiryRequested = AccountExpiryRequestedEvent
