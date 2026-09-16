from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.base import Model


class SkillExperienceModel(Model):
    __tablename__ = 'learning_skill_experiences'

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
