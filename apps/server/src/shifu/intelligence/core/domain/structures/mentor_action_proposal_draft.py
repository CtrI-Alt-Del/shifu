from shifu.intelligence.core.domain.enums.mentor_action_kind import MentorActionKind
from shifu.intelligence.core.domain.structures.mentor_action_candidate_goal import (
    MentorActionCandidateGoal,
)
from shifu.shared.core.domain.structures import structure


@structure
class MentorActionProposalDraft:
    kind: MentorActionKind
    skill_id: str
    skill_name: str
    goal_id: str | None  # fixed destination, else None
    goal_title: str | None
    skill_experience_id: str | None  # removal with a fixed destination
    candidate_goals: tuple[MentorActionCandidateGoal, ...]  # empty when fixed
    justification: str | None  # add only
