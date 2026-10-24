from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from shifu.intelligence.core.domain.enums.mentor_action_kind import MentorActionKind
from shifu.intelligence.core.domain.enums.mentor_action_proposal_status import (
    MentorActionProposalStatus,
)
from shifu.intelligence.core.domain.errors.mentor_action_proposal_finalized_error import (
    MentorActionProposalFinalizedError,
)
from shifu.shared.core.domain.entities import entity

if TYPE_CHECKING:
    from datetime import datetime

    from shifu.intelligence.core.domain.enums.mentor_action_proposal_outcome import (
        MentorActionProposalOutcome,
    )
    from shifu.intelligence.core.domain.enums.mentor_action_proposal_rejection_reason import (
        MentorActionProposalRejectionReason,
    )
    from shifu.intelligence.core.domain.structures.mentor_action_candidate_goal import (
        MentorActionCandidateGoal,
    )
    from shifu.intelligence.core.domain.structures.mentor_action_proposal_draft import (
        MentorActionProposalDraft,
    )


@entity
class MentorActionProposal:
    """One operation the Mentor proposes in a conversation, confirmed only by the learner."""

    MAX_JUSTIFICATION_CODE_POINTS: ClassVar[int] = 2000

    id: str
    account_id: str
    session_id: str
    learner_message_id: str
    attempt_id: str
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
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        id: str,
        account_id: str,
        session_id: str,
        learner_message_id: str,
        attempt_id: str,
        draft: MentorActionProposalDraft,
        created_at: datetime,
    ) -> MentorActionProposal:
        if not all(
            (
                id,
                account_id,
                session_id,
                learner_message_id,
                attempt_id,
                draft.skill_id,
                draft.skill_name,
            )
        ):
            raise ValueError('Incomplete action proposal')
        if created_at.tzinfo is None:
            raise ValueError('Invalid action proposal timestamp')
        cls._validate_destination(draft)
        cls._validate_kind(draft)
        return cls(
            id=id,
            account_id=account_id,
            session_id=session_id,
            learner_message_id=learner_message_id,
            attempt_id=attempt_id,
            kind=draft.kind,
            skill_id=draft.skill_id,
            skill_name=draft.skill_name,
            goal_id=draft.goal_id,
            goal_title=draft.goal_title,
            skill_experience_id=draft.skill_experience_id,
            candidate_goals=draft.candidate_goals,
            justification=draft.justification,
            status=MentorActionProposalStatus.PENDING,
            outcome=None,
            rejection_reason=None,
            resolved_goal_id=None,
            resolved_skill_experience_id=None,
            created_at=created_at,
            updated_at=created_at,
        )

    def decline(self, now: datetime) -> None:
        """Only a pending proposal can be declined."""
        if self.status is not MentorActionProposalStatus.PENDING:
            raise MentorActionProposalFinalizedError
        self.status = MentorActionProposalStatus.DECLINED
        self.updated_at = now

    def resolve(
        self,
        outcome: MentorActionProposalOutcome | None,
        rejection_reason: MentorActionProposalRejectionReason | None,
        goal_id: str,
        skill_experience_id: str | None,
        now: datetime,
    ) -> bool:
        """Record the Learning outcome; an outcome may replace ``declined`` only.

        Returns ``False`` without changes when the proposal is already final,
        including a repeated delivery of the same outcome.
        """
        if (outcome is None) == (rejection_reason is None):
            raise ValueError('A resolution carries an outcome or a rejection reason')
        if self.status in (
            MentorActionProposalStatus.COMPLETED,
            MentorActionProposalStatus.REJECTED,
        ):
            return False
        self.status = (
            MentorActionProposalStatus.REJECTED
            if rejection_reason is not None
            else MentorActionProposalStatus.COMPLETED
        )
        self.outcome = outcome
        self.rejection_reason = rejection_reason
        self.resolved_goal_id = goal_id
        self.resolved_skill_experience_id = skill_experience_id
        self.updated_at = now
        return True

    @classmethod
    def _validate_destination(cls, draft: MentorActionProposalDraft) -> None:
        if draft.goal_id is not None:
            if not draft.goal_title or draft.candidate_goals:
                raise ValueError('A fixed destination carries no candidates')
            return
        if (
            draft.goal_title is not None
            or draft.skill_experience_id is not None
            or not draft.candidate_goals
        ):
            raise ValueError('An open destination lists its candidate Objectives')

    @classmethod
    def _validate_kind(cls, draft: MentorActionProposalDraft) -> None:
        if draft.kind is MentorActionKind.ADD_SKILL:
            justification = draft.justification
            if (
                draft.skill_experience_id is not None
                or justification is None
                or not 1 <= len(justification) <= cls.MAX_JUSTIFICATION_CODE_POINTS
            ):
                raise ValueError('An addition carries a bounded justification')
            return
        if draft.justification is not None:
            raise ValueError('A removal carries no justification')
        if draft.goal_id is not None:
            if draft.skill_experience_id is None:
                raise ValueError('A removal targets one experience')
            return
        if not all(
            candidate.contains_skill and candidate.skill_experience_id is not None
            for candidate in draft.candidate_goals
        ):
            raise ValueError('Removal candidates hold the Skill')
