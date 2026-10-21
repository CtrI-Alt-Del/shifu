from shifu.intelligence.core.domain.entities import MentorMessage
from shifu.shared.core.domain.structures import structure


@structure
class MentorMessagesPage:
    items: list[MentorMessage]
    next_cursor: str | None
