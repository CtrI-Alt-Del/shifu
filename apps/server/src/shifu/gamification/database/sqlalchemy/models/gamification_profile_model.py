from datetime import date, datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class GamificationProfileModel(Model):
    __tablename__ = 'gamification_profiles'
    __table_args__ = (
        Index('ix_gamification_profile_account_id', 'account_id', unique=True),
        CheckConstraint(
            'reminder_hour BETWEEN 6 AND 22',
            name='ck_gamification_profiles_reminder_hour',
        ),
        Index(
            'ix_gamification_profiles_streak_latest_practice_date',
            'streak_latest_practice_date',
        ),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(26), nullable=False)
    total_xp: Mapped[int] = mapped_column(Integer, nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    streak_current: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default='0'
    )
    streak_longest: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default='0'
    )
    streak_latest_practice_date: Mapped[date | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    reminder_hour: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default='18'
    )
    reminder_invite_answered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
