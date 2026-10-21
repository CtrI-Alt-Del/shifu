from shifu.shared.core.domain.structures import structure


@structure
class MentorContextHint:
    goal_id: str | None = None
    skill_id: str | None = None
    competency_id: str | None = None
    material_id: str | None = None
    activity_id: str | None = None
