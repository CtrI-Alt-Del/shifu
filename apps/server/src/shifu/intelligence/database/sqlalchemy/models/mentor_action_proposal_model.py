from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class MentorActionProposalModel(Model):
    __tablename__ = 'intelligence_mentor_action_proposals'
    __table_args__ = (
        CheckConstraint(
            "kind IN ('add_skill', 'remove_skill')",
            name='ck_mentor_action_proposal_kind',
        ),
        CheckConstraint(
            "status IN ('pending', 'declined', 'completed', 'rejected')",
            name='ck_mentor_action_proposal_status',
        ),
        CheckConstraint(
            "outcome IS NULL OR outcome IN ('added', 'already_present', 'removed')",
            name='ck_mentor_action_proposal_outcome',
        ),
        CheckConstraint(
            'rejection_reason IS NULL OR rejection_reason IN '
            "('goal_unavailable', 'skill_unavailable', 'experience_unavailable')",
            name='ck_mentor_action_proposal_rejection_reason',
        ),
        CheckConstraint(
            "(status = 'completed') = (outcome IS NOT NULL) "
            "AND (status = 'rejected') = (rejection_reason IS NOT NULL)",
            name='ck_mentor_action_proposal_resolution',
        ),
        CheckConstraint(
            "jsonb_typeof(candidate_goals) = 'array'",
            name='ck_mentor_action_proposal_candidates',
        ),
        Index(
            'ix_mentor_action_proposal_session_status',
            'account_id',
            'session_id',
            'status',
        ),
        Index('ix_mentor_action_proposal_attempt', 'attempt_id'),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(26), nullable=False)
    session_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('intelligence_mentor_sessions.id', ondelete='CASCADE'),
        nullable=False,
    )
    learner_message_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('intelligence_mentor_messages.id', ondelete='CASCADE'),
        nullable=False,
    )
    attempt_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('intelligence_mentor_response_attempts.id', ondelete='CASCADE'),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    outcome: Mapped[str | None] = mapped_column(String(16), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    skill_id: Mapped[str] = mapped_column(String(255), nullable=False)
    skill_name: Mapped[str] = mapped_column(String(255), nullable=False)
    goal_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    goal_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    skill_experience_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_goals: Mapped[list[dict[str, str | bool | None]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    justification: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    resolved_goal_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolved_skill_experience_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
