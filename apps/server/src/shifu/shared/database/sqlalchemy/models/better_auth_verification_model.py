from datetime import datetime

from sqlalchemy import (
    DateTime,
    Index,
    PrimaryKeyConstraint,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class BetterAuthVerificationModel(Model):
    __tablename__ = 'better_auth_verifications'
    __table_args__ = (
        UniqueConstraint(
            'identifier',
            name='uq_better_auth_verifications_identifier',
        ),
        PrimaryKeyConstraint('id', name='pk_better_auth_verifications'),
        Index('ix_better_auth_verifications_expires_at', 'expires_at'),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    identifier: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP'),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP'),
    )
