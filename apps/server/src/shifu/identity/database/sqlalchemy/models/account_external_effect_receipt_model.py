from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    PrimaryKeyConstraint,
    String,
    func,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class AccountExternalEffectReceiptModel(Model):
    __tablename__ = 'identity_account_external_effect_receipts'
    __table_args__ = (
        CheckConstraint(
            "state IN ('in_flight', 'settled', 'unknown')",
            name='ck_identity_account_external_effect_receipts_state',
        ),
        CheckConstraint(
            'length(trim(operation)) BETWEEN 1 AND 120',
            name='ck_identity_account_external_effect_receipts_operation',
        ),
        Index(
            'ix_identity_account_external_effect_receipts_account_state',
            'account_id',
            'state',
        ),
        PrimaryKeyConstraint(
            'account_id',
            'effect_id',
            name='pk_identity_account_external_effect_receipts',
        ),
    )

    account_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    effect_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True), primary_key=True
    )
    operation: Mapped[str] = mapped_column(String(120), nullable=False)
    admitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    state: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'in_flight'")
    )
