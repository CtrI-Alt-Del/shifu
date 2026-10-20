from shifu.intelligence.core.domain.structures.mentor_summary_marker import (
    MentorSummaryMarker,
)
from shifu.shared.core.domain.structures import structure


@structure
class MentorSessionSummaryState:
    current: MentorSummaryMarker | None = None
    failure_after_message_id: str | None = None
