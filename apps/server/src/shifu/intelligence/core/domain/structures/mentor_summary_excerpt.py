from shifu.intelligence.core.domain.enums import MentorSummaryExcerptKind
from shifu.shared.core.domain.structures import structure


@structure
class MentorSummaryExcerpt:
    message_id: str
    kind: MentorSummaryExcerptKind
    text: str
