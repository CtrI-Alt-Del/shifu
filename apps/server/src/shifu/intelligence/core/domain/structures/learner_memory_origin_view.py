from datetime import datetime

from shifu.shared.core.domain.structures import structure


@structure
class LearnerMemoryOriginView:
    session_id: str
    message_id: str | None
    conversation_title: str | None  # null when the conversation is deleted
    is_available: bool
    declared_at: datetime
