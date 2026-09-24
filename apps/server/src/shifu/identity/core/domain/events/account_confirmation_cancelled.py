from dataclasses import field

from shifu.identity.core.domain.enums import AccountConfirmationCancellationReason
from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class AccountConfirmationCancelledPayload:
    communication_id: str
    identity_confirmation_id: str
    reason: AccountConfirmationCancellationReason


@structure
class AccountConfirmationCancelledEvent(Event[AccountConfirmationCancelledPayload]):
    name: str = field(default='identity.account-confirmation-cancelled', init=False)


AccountConfirmationCancelled = AccountConfirmationCancelledEvent
