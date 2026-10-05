from datetime import datetime

from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.shared.core.domain.structures import NonEmptyText, structure


@structure
class MessageTemplateValues:
    """The declared values accepted by the transactional e-mail templates."""

    action_url: str
    expires_at: datetime
    display_name: str | None = None

    def __post_init__(self) -> None:
        if self.display_name is not None:
            object.__setattr__(
                self,
                'display_name',
                NonEmptyText.create(
                    self.display_name, error_type=InvalidCommunicationError
                ).value,
            )
        object.__setattr__(
            self,
            'action_url',
            NonEmptyText.create(
                self.action_url, error_type=InvalidCommunicationError
            ).value,
        )


AccountConfirmationMessageValues = MessageTemplateValues
PasswordRecoveryMessageValues = MessageTemplateValues
