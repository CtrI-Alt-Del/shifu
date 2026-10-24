from shifu.shared.core.domain.structures.structure import structure


@structure
class MentorGoalDestination:
    goal_id: str
    title: str
    skill_experience_id: str | None
