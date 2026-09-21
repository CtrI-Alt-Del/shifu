from datetime import datetime

from sqlalchemy import DateTime, Index, PrimaryKeyConstraint, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class BetterAuthJwksModel(Model):
    __tablename__ = 'better_auth_jwks'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='pk_better_auth_jwks'),
        Index('ix_better_auth_jwks_expires_at', 'expires_at'),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    public_key: Mapped[str] = mapped_column(Text, nullable=False)
    private_key: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP'),
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
