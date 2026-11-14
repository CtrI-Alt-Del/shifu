from datetime import datetime

from shifu.intelligence.core.domain.enums.mentor_action_kind import MentorActionKind
from shifu.intelligence.core.domain.enums.mentor_action_proposal_outcome import (
    MentorActionProposalOutcome,
)
from shifu.intelligence.core.domain.enums.mentor_action_proposal_rejection_reason import (
    MentorActionProposalRejectionReason,
)
from shifu.intelligence.core.domain.enums.mentor_action_proposal_status import (
    MentorActionProposalStatus,
)
from shifu.intelligence.core.domain.structures.mentor_action_candidate_goal import (
    MentorActionCandidateGoal,
)
from shifu.shared.core.domain.structures import structure


@structure
class MentorActionProposalItem:
    """Read projection of one proposal in the conversation timeline."""

    id: str
    source_message_id: str
    kind: MentorActionKind
    skill_id: str
    skill_name: str
    goal_id: str | None
    goal_title: str | None
    skill_experience_id: str | None
    candidate_goals: tuple[MentorActionCandidateGoal, ...]
    justification: str | None
    status: MentorActionProposalStatus
    outcome: MentorActionProposalOutcome | None
    rejection_reason: MentorActionProposalRejectionReason | None
    resolved_goal_id: str | None
    resolved_skill_experience_id: str | None
    created_at: datetime
