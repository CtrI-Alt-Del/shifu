from shifu.learning.core.domain.structures.goal_skill_detail import GoalSkillDetail
from shifu.learning.core.domain.structures.goal_skill_relation import GoalSkillRelation
from shifu.shared.core.domain.structures import structure


@structure
class GoalDetail:
    goal_id: str
    title: str
    description: str
    skills: tuple[GoalSkillDetail, ...]
    relations: tuple[GoalSkillRelation, ...]
