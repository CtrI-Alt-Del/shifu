from shifu.intelligence.core.domain.structures.mentor_summary_excerpt_span import (
    MentorSummaryExcerptSpan,
)
from shifu.shared.core.domain.structures import structure


@structure
class MentorConversationSummaryDraft:
    topics: tuple[str, ...]  # <= 8, each non-empty, <= 80 code points
    excerpts: tuple[MentorSummaryExcerptSpan, ...]  # <= 5 doubt + <= 5 guidance
    algorithm_version: str
