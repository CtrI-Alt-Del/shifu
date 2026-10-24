from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class ActivityXpBalanceModel(Model):
    __tablename__ = 'gamification_activity_xp_balances'
    __table_args__ = (
        UniqueConstraint(
            'account_id',
            'activity_id',
            name='uq_gamification_activity_xp_balance_account_activity',
        ),
        Index('ix_gamification_activity_xp_balance_account_id', 'account_id'),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(26), nullable=False)
    activity_id: Mapped[str] = mapped_column(String(26), nullable=False)
    maximum_xp: Mapped[int] = mapped_column(Integer, nullable=False)
    granted_xp: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
