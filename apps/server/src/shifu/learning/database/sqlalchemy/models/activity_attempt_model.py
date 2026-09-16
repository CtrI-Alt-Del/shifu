from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.base import Model


class ActivityAttemptModel(Model):
    __tablename__ = 'learning_activity_attempts'

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
