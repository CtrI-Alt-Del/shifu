from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class AiQuotaMonthModel(Model):
    __tablename__ = 'intelligence_ai_quota_months'
    __table_args__ = (
        CheckConstraint('used_units >= 0', name='ck_ai_quota_month_used_units'),
        CheckConstraint('limit_units > 0', name='ck_ai_quota_month_limit_units'),
        CheckConstraint(
            'EXTRACT(DAY FROM month) = 1', name='ck_ai_quota_month_first_day'
        ),
    )

    account_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    month: Mapped[date] = mapped_column(Date, primary_key=True)
    used_units: Mapped[int] = mapped_column(BigInteger, nullable=False)
    limit_units: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
