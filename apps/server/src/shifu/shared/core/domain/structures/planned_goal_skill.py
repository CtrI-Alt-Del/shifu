from shifu.shared.core.domain.structures.structure import structure


@structure
class PlannedGoalSkill:
    """One Skill of a confirmed Planner proposal with its inclusion rationale."""

    skill_id: str
    inclusion_reason: str
