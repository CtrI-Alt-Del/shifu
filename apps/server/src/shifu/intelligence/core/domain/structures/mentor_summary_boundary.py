from datetime import datetime

from shifu.shared.core.domain.structures import structure


@structure
class MentorSummaryBoundary:
    message_id: str
    created_at: datetime  # UTC; ordering is (created_at, message_id)
