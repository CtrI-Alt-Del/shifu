from datetime import datetime

from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.shared.core.domain.structures import structure


@structure
class ResumeItem:
    skill_experience_id: str
    goal_id: str
    goal_title: str
    skill_id: str
    skill_name: str
    status: SkillExperienceStatus  # DIAGNOSING or LEARNING only
    focus_competency_name: str | None  # LEARNING only
    last_submitted_at: datetime | None
