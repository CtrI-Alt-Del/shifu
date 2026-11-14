from shifu.shared.core.domain.structures import structure


@structure
class MentorActionCandidateGoal:
    goal_id: str
    title: str
    contains_skill: bool
    skill_experience_id: str | None
