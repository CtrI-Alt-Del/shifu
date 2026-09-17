from shifu.shared.core.domain.structures import structure


@structure
class PlannedSkill:
    skill_id: str
    inclusion_reason: str
