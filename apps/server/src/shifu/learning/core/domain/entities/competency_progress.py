from datetime import datetime
from decimal import Decimal

from shifu.learning.core.domain.enums import CompetencyProgressStatus
from shifu.shared.core.domain.entities import entity


@entity
class CompetencyProgress:
    id: str
    skill_experience_id: str
    competency_id: str
    content_released: bool
    created_at: datetime
    updated_at: datetime
    initial_progress: Decimal | None = None
    current_progress: Decimal | None = None
    status: CompetencyProgressStatus | None = None
    mastered_at: datetime | None = None
