from shifu.shared.core.domain.structures import structure


@structure
class GoalSkillRelation:
    foundation_skill_id: str
    skill_id: str
