from datetime import datetime

from shifu.intelligence.core.domain.enums import MentorMessageRole
from shifu.shared.core.domain.entities import frozen_entity


@frozen_entity
class MentorMessage:
    id: str
    session_id: str
    role: MentorMessageRole
    content: str
    created_at: datetime
    in_reply_to_message_id: str | None
