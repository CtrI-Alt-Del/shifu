from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class SkillExperienceModel(Model):
    __tablename__ = 'learning_skill_experiences'
    __table_args__ = (
        UniqueConstraint(
            'goal_id',
            'skill_id',
            name='uq_learning_skill_experience_goal_skill',
        ),
        Index('ix_learning_skill_experience_goal_id', 'goal_id'),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    goal_id: Mapped[str] = mapped_column(
        String(26), ForeignKey('learning_goals.id', ondelete='CASCADE'), nullable=False
    )
    skill_id: Mapped[str] = mapped_column(String(26), nullable=False)
    inclusion_reason: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completion_summary: Mapped[object | None] = mapped_column(JSON, nullable=True)
    policy_id: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default='learning-v1'
    )
    recommended_concept_id: Mapped[str | None] = mapped_column(
        String(26), nullable=True
    )
