from datetime import datetime

from shifu.shared.core.domain.structures import structure


@structure
class MentorSummaryMarker:
    version: int
    boundary_message_id: str
    covered_message_count: int
    completed_at: datetime
    after_message_id: str | None = None  # learner message that triggered the summary
