from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class GoalConfirmationModel(Model):
    __tablename__ = 'learning_goal_confirmations'
    __table_args__ = (Index('ix_learning_goal_confirmation_goal_id', 'goal_id'),)

    account_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    confirmation_key: Mapped[str] = mapped_column(String(36), primary_key=True)
    planning_id: Mapped[str] = mapped_column(String(26), nullable=False)
    goal_id: Mapped[str] = mapped_column(
        String(26), ForeignKey('learning_goals.id', ondelete='CASCADE'), nullable=False
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
