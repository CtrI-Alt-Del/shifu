from datetime import datetime

from shifu.shared.core.domain.entities import entity


@entity
class Goal:
    id: str
    account_id: str
    title: str
    description: str
    created_at: datetime
    updated_at: datetime
