from datetime import datetime

from sqlalchemy import DateTime, Index, JSON, String, text
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class CommunicationModel(Model):
    __tablename__ = 'communication_messages'
    __table_args__ = (
        Index(
            'uq_communication_messages_identity_confirmation_id',
            'identity_confirmation_id',
            unique=True,
            postgresql_where=text('identity_confirmation_id IS NOT NULL'),
        ),
        Index(
            'ix_communication_messages_status_next_attempt_at',
            'status',
            'next_attempt_at',
        ),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    account_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    recipient_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    recipient_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    content: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failure_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attempt_count: Mapped[int] = mapped_column(nullable=False)
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    identity_confirmation_id: Mapped[str | None] = mapped_column(
        String(26), nullable=True
    )
    encrypted_content: Mapped[dict[str, object] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    redacted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
