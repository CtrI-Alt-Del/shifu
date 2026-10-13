from shifu.intelligence.core.domain.enums import MentorIntent
from shifu.shared.core.domain.structures import structure


@structure
class MentorResponseBlock:
    block_key: str
    ordinal: int
    intent: MentorIntent | None
    content: str
