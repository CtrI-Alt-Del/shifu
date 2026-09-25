from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, text
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class ActivityAttemptModel(Model):
    __tablename__ = 'learning_activity_attempts'
    __table_args__ = (
        Index(
            'ix_learning_attempt_experience_activity_submitted',
            'skill_experience_id',
            'activity_id',
            'submitted_at',
        ),
        Index(
            'uq_learning_attempt_experience_submission_key',
            'skill_experience_id',
            'submission_key',
            unique=True,
            postgresql_where=text('submission_key IS NOT NULL'),
        ),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    skill_experience_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('learning_skill_experiences.id', ondelete='CASCADE'),
        nullable=False,
    )
    competency_id: Mapped[str] = mapped_column(String(26), nullable=False)
    activity_id: Mapped[str] = mapped_column(String(26), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    answers: Mapped[object] = mapped_column(JSON, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    submission_key: Mapped[str | None] = mapped_column(String(36), nullable=True)
    grading_snapshot: Mapped[object | None] = mapped_column(JSON, nullable=True)
