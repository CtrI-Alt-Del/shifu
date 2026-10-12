from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class EarnedAchievementModel(Model):
    __tablename__ = 'gamification_earned_achievements'
    __table_args__ = (
        UniqueConstraint(
            'account_id',
            'achievement_id',
            name='uq_gamification_earned_achievement_account_achievement',
        ),
        Index('ix_gamification_earned_achievement_account_id', 'account_id'),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(26), nullable=False)
    achievement_id: Mapped[str] = mapped_column(String(80), nullable=False)
    achievement_name: Mapped[str] = mapped_column(String(120), nullable=False)
    criterion: Mapped[object] = mapped_column(JSON, nullable=False)
    xp_reward: Mapped[int] = mapped_column(Integer, nullable=False)
    achieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
