from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import require_non_empty


@structure
class MessageContent:
    subject: str
    html: str
    text: str | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, 'subject', require_non_empty(self.subject, InvalidCommunicationError)
        )
        object.__setattr__(
            self, 'html', require_non_empty(self.html, InvalidCommunicationError)
        )
