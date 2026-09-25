from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class ConceptObservationModel(Model):
    __tablename__ = 'learning_concept_observations'
    __table_args__ = (
        Index(
            'ix_learning_concept_observation_experience_concept_completed',
            'skill_experience_id',
            'concept_id',
            'completed_at',
        ),
    )

    attempt_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('learning_activity_attempts.id', ondelete='CASCADE'),
        primary_key=True,
    )
    concept_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    skill_experience_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('learning_skill_experiences.id', ondelete='CASCADE'),
        nullable=False,
    )
    competency_id: Mapped[str] = mapped_column(String(26), nullable=False)
    activity_id: Mapped[str] = mapped_column(String(26), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(16), nullable=False)
    first_submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    question_scores: Mapped[object] = mapped_column(JSON, nullable=False)
    diagnostic: Mapped[bool] = mapped_column(Boolean, nullable=False)
