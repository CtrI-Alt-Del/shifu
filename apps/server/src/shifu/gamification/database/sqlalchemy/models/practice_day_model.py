from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class PracticeDayModel(Model):
    __tablename__ = 'gamification_practice_days'
    __table_args__ = (
        UniqueConstraint(
            'account_id',
            'practice_date',
            name='uq_gamification_practice_day_account_date',
        ),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(26), nullable=False)
    practice_date: Mapped[date] = mapped_column(Date, nullable=False)
    time_zone: Mapped[str] = mapped_column(String(64), nullable=False)
    practiced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    recognized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
