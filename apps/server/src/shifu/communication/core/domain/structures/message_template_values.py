from datetime import datetime

from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import require_non_empty


@structure
class MessageTemplateValues:
    """The declared values accepted by the transactional e-mail templates."""

    display_name: str
    action_url: str
    expires_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            'display_name',
            require_non_empty(self.display_name, InvalidCommunicationError),
        )
        object.__setattr__(
            self,
            'action_url',
            require_non_empty(self.action_url, InvalidCommunicationError),
        )


AccountConfirmationMessageValues = MessageTemplateValues
PasswordRecoveryMessageValues = MessageTemplateValues
