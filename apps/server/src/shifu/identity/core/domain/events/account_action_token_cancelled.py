from dataclasses import field

from shifu.identity.core.domain.enums import AccountActionTokenCancellationReason
from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class AccountActionTokenCancelledPayload:
    communication_id: str
    identity_action_token_id: str
    reason: AccountActionTokenCancellationReason


@structure
class AccountActionTokenCancelledEvent(Event[AccountActionTokenCancelledPayload]):
    name: str = field(default='identity.action-token-cancelled', init=False)


AccountActionTokenCancelled = AccountActionTokenCancelledEvent
