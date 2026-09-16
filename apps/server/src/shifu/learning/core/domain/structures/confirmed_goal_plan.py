from shifu.learning.core.domain.structures.planned_skill import PlannedSkill
from shifu.shared.core.domain.structures import structure


@structure
class ConfirmedGoalPlan:
    title: str
    description: str
    skills: tuple[PlannedSkill, ...]
