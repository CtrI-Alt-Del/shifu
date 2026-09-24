from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.shared.core.domain.structures import structure


@structure
class GoalSkillDetail:
    skill_id: str
    skill_name: str
    status: SkillExperienceStatus
    policy_id: str
