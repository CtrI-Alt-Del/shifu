from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.shared.core.domain.structures import structure


@structure
class SkillExperienceReference:
    goal_id: str
    goal_title: str
    skill_experience_id: str
    skill_id: str
    status: SkillExperienceStatus
