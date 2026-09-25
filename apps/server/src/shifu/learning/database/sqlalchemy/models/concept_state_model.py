from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class ConceptStateModel(Model):
    __tablename__ = 'learning_concept_states'
    __table_args__ = (
        Index(
            'ix_learning_concept_state_experience_competency',
            'skill_experience_id',
            'competency_id',
        ),
        CheckConstraint(
            'initial_progress IS NULL OR (initial_progress >= 0 AND initial_progress <= 100)',
            name='ck_learning_concept_state_initial_progress',
        ),
        CheckConstraint(
            'current_progress IS NULL OR (current_progress >= 0 AND current_progress <= 100)',
            name='ck_learning_concept_state_current_progress',
        ),
    )

    skill_experience_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('learning_skill_experiences.id', ondelete='CASCADE'),
        primary_key=True,
    )
    concept_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    competency_id: Mapped[str] = mapped_column(String(26), nullable=False)
    initial_progress: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 12), nullable=True
    )
    current_progress: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 12), nullable=True
    )
    observed_difficulties: Mapped[object] = mapped_column(JSON, nullable=False)
    distinct_activity_ids: Mapped[object] = mapped_column(JSON, nullable=False)
    hard_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False)
    evidence_verification: Mapped[bool] = mapped_column(Boolean, nullable=False)
    inconclusive_activity_ids: Mapped[object] = mapped_column(JSON, nullable=False)
    current_contributions: Mapped[object] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
