from decimal import Decimal
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.shared.core.domain.structures import structure


@structure
class GoalSkillDetail:
    skill_experience_id: str
    skill_id: str
    name: str
    skill_name: str
    status: SkillExperienceStatus
    progress: Decimal | None
    inclusion_reason: str | None
    policy_id: str
