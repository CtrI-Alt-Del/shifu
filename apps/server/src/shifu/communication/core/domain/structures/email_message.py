from shifu.shared.core.domain.structures import structure


@structure
class EmailMessage:
    idempotency_key: str
    to: str
    subject: str
    html: str
