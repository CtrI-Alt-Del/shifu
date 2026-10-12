from datetime import datetime
from sqlalchemy import (
    String,
    DateTime,
    ForeignKeyConstraint,
    Index,
    CheckConstraint,
    text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from shifu.shared.database.sqlalchemy.model import Model


class MentorResponseAttemptModel(Model):
    __tablename__ = 'intelligence_mentor_response_attempts'
    __table_args__ = (
        UniqueConstraint('session_id', 'id', name='uq_mentor_attempt_session'),
        ForeignKeyConstraint(
            ['session_id', 'account_id'],
            [
                'intelligence_mentor_sessions.id',
                'intelligence_mentor_sessions.account_id',
            ],
            ondelete='CASCADE',
        ),
        ForeignKeyConstraint(
            ['session_id', 'learner_message_id'],
            [
                'intelligence_mentor_messages.session_id',
                'intelligence_mentor_messages.id',
            ],
            ondelete='CASCADE',
        ),
        Index(
            'uq_mentor_active_attempt',
            'session_id',
            unique=True,
            postgresql_where=text("status IN ('queued', 'processing')"),
        ),
        CheckConstraint(
            "status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')",
            name='ck_mentor_attempt_status',
        ),
        Index('ix_mentor_attempt_current', 'session_id', 'created_at', 'id'),
    )
    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(26), nullable=False)
    session_id: Mapped[str] = mapped_column(String(26), nullable=False)
    learner_message_id: Mapped[str] = mapped_column(String(26), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    context_hint: Mapped[dict[str, str | None] | None] = mapped_column(
        JSONB, nullable=True
    )
    access_revision: Mapped[str] = mapped_column(String(128), nullable=False)
    execution_owner: Mapped[str | None] = mapped_column(String(26), nullable=True)
    execution_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_reference_ids: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    generation_keys: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    usage_calls: Mapped[list[dict[str, str | int | float | None]] | None] = (
        mapped_column(JSONB, nullable=True, default=list)
    )
    operation_key: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
