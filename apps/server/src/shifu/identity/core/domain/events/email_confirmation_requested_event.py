from dataclasses import field

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class EmailConfirmationRequestedPayload:
    account_id: str
    account_action_token_id: str
    email: str
    display_name: str
    expires_at: str
    requested_at: str


@structure
class EmailConfirmationRequestedEvent(Event[EmailConfirmationRequestedPayload]):
    name: str = field(default='identity/email-confirmation.requested', init=False)
