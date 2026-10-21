from dataclasses import field
from typing import ClassVar

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class AccountDeletedPayload:
    account_id: str
    deleted_at: str


@structure
class AccountDeletedEvent(Event[AccountDeletedPayload]):
    EVENT_NAME: ClassVar[str] = 'identity/account.deleted'
    name: str = field(default=EVENT_NAME, init=False)
