from datetime import datetime

from shifu.shared.core.domain.entities import entity


@entity
class PlanningSession:
    id: str
    account_id: str
    initial_intent: str
    created_at: datetime
