from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class CompetencyProgressModel(Model):
    __tablename__ = 'learning_competency_progresses'
    __table_args__ = (
        CheckConstraint(
            'hard_activity_score >= 0 AND hard_activity_score <= 100',
            name='ck_learning_competency_progress_hard_score',
        ),
        UniqueConstraint(
            'skill_experience_id',
            'competency_id',
            name='uq_learning_competency_progress_experience_competency',
        ),
        Index(
            'ix_learning_competency_progress_experience_competency',
            'skill_experience_id',
            'competency_id',
        ),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    skill_experience_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('learning_skill_experiences.id', ondelete='CASCADE'),
        nullable=False,
    )
    competency_id: Mapped[str] = mapped_column(String(26), nullable=False)
    content_released: Mapped[bool] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    initial_progress: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    current_progress: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    hard_activity_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    mastered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
