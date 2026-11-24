from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    String,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class AccountErasureModel(Model):
    __tablename__ = 'identity_account_erasures'
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'completed')",
            name='ck_identity_account_erasures_status',
        ),
        Index('ix_identity_account_erasures_pending_due', 'status', 'due_at'),
        PrimaryKeyConstraint('erasure_id', name='pk_identity_account_erasures'),
    )

    erasure_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True), primary_key=True
    )
    account_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'pending'")
    )
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AccountErasureParticipantModel(Model):
    __tablename__ = 'identity_account_erasure_participants'
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'acknowledged')",
            name='ck_identity_account_erasure_participants_status',
        ),
        PrimaryKeyConstraint(
            'erasure_id',
            'participant',
            name='uq_identity_account_erasure_participants_erasure_participant',
        ),
    )

    erasure_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey(
            'identity_account_erasures.erasure_id',
            name='fk_identity_account_erasure_participants_erasure_id',
            ondelete='CASCADE',
        ),
        primary_key=True,
        nullable=False,
    )
    participant: Mapped[str] = mapped_column(String(80), primary_key=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'pending'")
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
