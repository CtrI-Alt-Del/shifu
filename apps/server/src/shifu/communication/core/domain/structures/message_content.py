from shifu.shared.core.domain.structures import structure


@structure
class MessageContent:
    subject: str
    html: str
    text: str | None
