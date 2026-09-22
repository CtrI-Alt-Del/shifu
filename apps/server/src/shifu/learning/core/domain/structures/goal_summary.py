from datetime import datetime

from shifu.shared.core.domain.structures import structure


@structure
class GoalSummary:
    id: str
    title: str
    description: str
    skill_count: int
    updated_at: datetime
