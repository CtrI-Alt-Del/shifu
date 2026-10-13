from shifu.shared.core.domain.structures.structure import structure


@structure
class MentorContextSnapshot:
    goal_id: str | None
    skill_experience_id: str | None
    skill_id: str | None
    competency_id: str | None
    activity_id: str | None
    skill_completed: bool | None
    diagnostic_in_progress: bool
    facts: tuple[tuple[str, str], ...]
    eligible_references: tuple[str, ...]
    resolved_references: tuple[str, ...]
    unavailable_sources: tuple[str, ...]
