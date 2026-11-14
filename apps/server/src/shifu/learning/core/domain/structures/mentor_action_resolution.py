from shifu.learning.core.domain.enums import (
    MentorActionOperation,
    MentorActionOutcome,
    MentorActionRejectionReason,
)
from shifu.shared.core.domain.structures import structure


@structure
class MentorActionResolution:
    confirmation_id: str
    operation: MentorActionOperation
    outcome: MentorActionOutcome
    rejection_reason: MentorActionRejectionReason | None
    goal_id: str
    skill_id: str | None
    skill_experience_id: str | None
