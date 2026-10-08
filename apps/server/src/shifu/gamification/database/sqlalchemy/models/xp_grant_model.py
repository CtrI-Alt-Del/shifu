from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class XpGrantModel(Model):
    __tablename__ = 'gamification_xp_grants'
    __table_args__ = (Index('ix_gamification_xp_grant_account_id', 'account_id'),)

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(26), nullable=False)
    fact_id: Mapped[str] = mapped_column(String(26), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    origin: Mapped[object] = mapped_column(JSON, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
