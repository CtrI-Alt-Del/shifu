from shifu.intelligence.core.domain.enums import MentorSummaryExcerptKind
from shifu.shared.core.domain.structures import structure


@structure
class MentorSummaryExcerptSpan:
    message_id: str
    start: int
    end: int
    kind: MentorSummaryExcerptKind
