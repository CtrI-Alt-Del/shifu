from dataclasses import field

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class AccountPasswordRecoveredPayload:
    account_id: str
    access_version: int
    recovered_at: str


@structure
class AccountPasswordRecoveredEvent(Event[AccountPasswordRecoveredPayload]):
    name: str = field(default='identity/account.password-recovered', init=False)
