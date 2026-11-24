from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    PrimaryKeyConstraint,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class AccountBrowserCapabilityModel(Model):
    __tablename__ = 'identity_account_browser_capabilities'
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'revoked')",
            name='ck_identity_account_browser_capabilities_status',
        ),
        Index('ix_identity_account_browser_capabilities_account', 'account_id'),
        PrimaryKeyConstraint(
            'capability_hash',
            name='pk_identity_account_browser_capabilities',
        ),
    )

    capability_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(26), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'active'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
