from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import normalize_email, require_non_empty


@structure
class EmailMessage:
    idempotency_key: str
    to: str
    subject: str
    html: str
    text: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            'idempotency_key',
            require_non_empty(self.idempotency_key, InvalidCommunicationError),
        )
        object.__setattr__(
            self,
            'to',
            normalize_email(self.to, InvalidCommunicationError),
        )
        object.__setattr__(
            self,
            'subject',
            require_non_empty(self.subject, InvalidCommunicationError),
        )
        object.__setattr__(
            self,
            'html',
            require_non_empty(self.html, InvalidCommunicationError),
        )
