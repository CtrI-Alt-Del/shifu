from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class MentorSessionSummaryModel(Model):
    __tablename__ = 'intelligence_mentor_session_summaries'
    __table_args__ = (
        UniqueConstraint('session_id', 'version', name='uq_mentor_summary_version'),
        CheckConstraint('version >= 1', name='ck_mentor_summary_version'),
        CheckConstraint(
            "status IN ('processing', 'ready', 'failed')",
            name='ck_mentor_summary_status',
        ),
        CheckConstraint(
            'covered_message_count > 0', name='ck_mentor_summary_covered_count'
        ),
        CheckConstraint(
            "failure_code IS NULL OR failure_code IN ('nlp_unavailable', 'invalid_output', 'exhausted')",
            name='ck_mentor_summary_failure_code',
        ),
        CheckConstraint(
            "(status = 'ready') = (topics IS NOT NULL AND excerpts IS NOT NULL "
            'AND algorithm_version IS NOT NULL AND completed_at IS NOT NULL)',
            name='ck_mentor_summary_ready_content',
        ),
        CheckConstraint(
            "(status = 'failed') = (failure_code IS NOT NULL)",
            name='ck_mentor_summary_failure',
        ),
        CheckConstraint(
            "status <> 'processing' OR attempt_id IS NOT NULL",
            name='ck_mentor_summary_processing_attempt',
        ),
        Index(
            'uq_mentor_summary_ready',
            'session_id',
            unique=True,
            postgresql_where=text("status = 'ready'"),
        ),
        Index(
            'uq_mentor_summary_active',
            'session_id',
            unique=True,
            postgresql_where=text("status = 'processing'"),
        ),
        Index('ix_mentor_summary_account', 'account_id'),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(26), nullable=False)
    session_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('intelligence_mentor_sessions.id', ondelete='CASCADE'),
        nullable=False,
    )
    attempt_id: Mapped[str | None] = mapped_column(
        String(26),
        ForeignKey('intelligence_mentor_response_attempts.id', ondelete='SET NULL'),
        nullable=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    boundary_message_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('intelligence_mentor_messages.id', ondelete='CASCADE'),
        nullable=False,
    )
    boundary_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    first_message_id: Mapped[str] = mapped_column(String(26), nullable=False)
    covered_message_count: Mapped[int] = mapped_column(Integer, nullable=False)
    topics: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    excerpts: Mapped[list[dict[str, str | int]] | None] = mapped_column(
        JSONB, nullable=True
    )
    algorithm_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
