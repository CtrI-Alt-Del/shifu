from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Index,
    String,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class AiQuotaChargeModel(Model):
    __tablename__ = 'intelligence_ai_quota_charges'
    __table_args__ = (
        CheckConstraint(
            "request_kind IN ('mentor_response', 'planning_operation')",
            name='ck_ai_quota_charge_kind',
        ),
        CheckConstraint('charged_units >= 0', name='ck_ai_quota_charge_charged_units'),
        Index('ix_intelligence_ai_quota_charges_account_id', 'account_id'),
    )

    request_kind: Mapped[str] = mapped_column(String(32), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(26), nullable=False)
    month: Mapped[date] = mapped_column(Date, nullable=False)
    charged_units: Mapped[int] = mapped_column(BigInteger, nullable=False)
    refunded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
