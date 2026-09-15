from datetime import datetime

from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.domain.structures import SkillCompletionSummary
from shifu.shared.core.domain.entities import entity


@entity
class SkillExperience:
    id: str
    goal_id: str
    skill_id: str
    inclusion_reason: str | None
    status: SkillExperienceStatus
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    completion_summary: SkillCompletionSummary | None = None
