from datetime import datetime

from shifu.shared.core.domain.entities import entity


@entity
class MentorSession:
    id: str
    account_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime
