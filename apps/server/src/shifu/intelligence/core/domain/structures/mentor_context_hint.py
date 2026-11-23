from shifu.shared.core.domain.structures import structure


@structure
class MentorContextHint:
    goal_id: str | None = None
    skill_id: str | None = None
    competency_id: str | None = None
    material_id: str | None = None
    activity_id: str | None = None
    # A route name from MENTOR_PAGE_LABELS: the page the learner is looking at.
    page: str | None = None
    # The key of the activity question on screen, among the activity_questions facts.
    question: str | None = None


def mentor_context_read_hints(hint: MentorContextHint | None) -> dict[str, str | None]:
    """The identifiers that select authorized context; the page never does."""
    if hint is None:
        return {}
    return {
        'goal_id': hint.goal_id,
        'skill_id': hint.skill_id,
        'competency_id': hint.competency_id,
        'material_id': hint.material_id,
        'activity_id': hint.activity_id,
    }
