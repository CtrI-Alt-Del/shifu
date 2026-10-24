from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class MentorActionReceiptModel(Model):
    __tablename__ = 'learning_mentor_action_receipts'
    __table_args__ = (
        UniqueConstraint(
            'account_id',
            'confirmation_id',
            name='uq_learning_mentor_action_receipt_confirmation',
        ),
        CheckConstraint(
            "operation IN ('add_skill','remove_skill')",
            name='ck_learning_mentor_action_receipt_operation',
        ),
        CheckConstraint(
            "outcome IN ('added','already_present','removed','rejected')",
            name='ck_learning_mentor_action_receipt_outcome',
        ),
        CheckConstraint(
            "rejection_reason IS NULL OR rejection_reason IN ('goal_unavailable','skill_unavailable','experience_unavailable')",
            name='ck_learning_mentor_action_receipt_rejection_reason',
        ),
        CheckConstraint(
            "(outcome = 'rejected') = (rejection_reason IS NOT NULL)",
            name='ck_learning_mentor_action_receipt_rejection_shape',
        ),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(26), nullable=False)
    confirmation_id: Mapped[str] = mapped_column(String(26), nullable=False)
    operation: Mapped[str] = mapped_column(String(16), nullable=False)
    goal_id: Mapped[str] = mapped_column(String(26), nullable=False)
    skill_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    skill_experience_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    resolved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
