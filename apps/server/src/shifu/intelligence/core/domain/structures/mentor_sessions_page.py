from shifu.intelligence.core.domain.entities import MentorSession
from shifu.shared.core.domain.structures import structure


@structure
class MentorSessionsPage:
    items: list[MentorSession]
    next_cursor: str | None
