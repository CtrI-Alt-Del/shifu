from datetime import datetime

from shifu.shared.core.domain.structures import structure


@structure
class LearnerMemoryOrigin:
    session_id: str
    message_id: str | None
    declared_at: datetime
