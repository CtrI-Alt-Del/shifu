from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.shared.core.domain.structures import EmailAddress, NonEmptyText, structure


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
            NonEmptyText.create(
                self.idempotency_key, error_type=InvalidCommunicationError
            ).value,
        )
        object.__setattr__(
            self,
            'to',
            EmailAddress.create(self.to, error_type=InvalidCommunicationError).value,
        )
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
