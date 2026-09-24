from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class AccountModel(Model):
    __tablename__ = 'identity_accounts'
    __table_args__ = (
        Index(
            'uq_identity_accounts_active_email',
            'email',
            unique=True,
            postgresql_where=text('deleted_at IS NULL'),
        ),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    access_version: Mapped[int] = mapped_column(Integer, nullable=False)
    time_zone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deletion_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
