from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    PrimaryKeyConstraint,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class BetterAuthSessionModel(Model):
    __tablename__ = 'better_auth_sessions'
    __table_args__ = (
        ForeignKeyConstraint(
            ['user_id'],
            ['better_auth_users.id'],
            name='fk_better_auth_sessions_user',
            ondelete='CASCADE',
        ),
        UniqueConstraint('token', name='uq_better_auth_sessions_token'),
        PrimaryKeyConstraint('id', name='pk_better_auth_sessions'),
        CheckConstraint(
            'access_version >= 1',
            name='ck_better_auth_sessions_access_version',
        ),
        Index('ix_better_auth_sessions_user_id', 'user_id'),
        Index('ix_better_auth_sessions_expires_at', 'expires_at'),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    token: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    access_version: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ip_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
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
