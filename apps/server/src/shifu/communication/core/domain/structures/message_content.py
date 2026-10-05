from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.shared.core.domain.structures import NonEmptyText, structure


@structure
class MessageContent:
    subject: str
    html: str
    text: str | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            'subject',
            NonEmptyText.create(
                self.subject, error_type=InvalidCommunicationError
            ).value,
        )
        object.__setattr__(
            self,
            'html',
            NonEmptyText.create(self.html, error_type=InvalidCommunicationError).value,
        )
