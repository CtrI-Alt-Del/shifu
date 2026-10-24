from datetime import datetime

from shifu.learning.core.domain.enums import (
    MentorActionOperation,
    MentorActionOutcome,
    MentorActionRejectionReason,
)
from shifu.shared.core.domain.entities import frozen_entity


@frozen_entity
class MentorActionReceipt:
    """Identifier-only record of a resolved Mentor confirmation."""

    id: str
    account_id: str
    confirmation_id: str
    operation: MentorActionOperation
    goal_id: str
    skill_id: str | None
    skill_experience_id: str | None
    outcome: MentorActionOutcome
    rejection_reason: MentorActionRejectionReason | None
    request_fingerprint: str
    resolved_at: datetime

    def __post_init__(self) -> None:
        is_rejected = self.outcome is MentorActionOutcome.REJECTED
        if is_rejected != (self.rejection_reason is not None):
            raise ValueError('A rejection reason is set only for rejected outcomes')

    @classmethod
    def create(
        cls,
        *,
        id: str,
        account_id: str,
        confirmation_id: str,
        operation: MentorActionOperation,
        goal_id: str,
        skill_id: str | None,
        skill_experience_id: str | None,
        outcome: MentorActionOutcome,
        rejection_reason: MentorActionRejectionReason | None,
        request_fingerprint: str,
        resolved_at: datetime,
    ) -> 'MentorActionReceipt':
        return cls(
            id=id,
            account_id=account_id,
            confirmation_id=confirmation_id,
            operation=operation,
            goal_id=goal_id,
            skill_id=skill_id,
            skill_experience_id=skill_experience_id,
            outcome=outcome,
            rejection_reason=rejection_reason,
            request_fingerprint=request_fingerprint,
            resolved_at=resolved_at,
        )
