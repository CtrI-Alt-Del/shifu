from datetime import datetime

from shifu.shared.core.domain.structures import structure


@structure
class AdaptiveCompetencyMemory:
    competency_id: str
    mastered_at: datetime | None = None
    content_released: bool = False
