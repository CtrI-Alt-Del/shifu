from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.shared.core.domain.structures import structure


@structure
class EvolutionOption:
    skill_experience_id: str
    goal_title: str
    skill_name: str
    status: SkillExperienceStatus  # DIAGNOSING, LEARNING or COMPLETED
