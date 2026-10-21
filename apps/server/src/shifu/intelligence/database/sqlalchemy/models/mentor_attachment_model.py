from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class MentorAttachmentModel(Model):
    __tablename__ = 'intelligence_mentor_attachments'
    __table_args__ = (
        ForeignKeyConstraint(
            ['session_id', 'account_id'],
            [
                'intelligence_mentor_sessions.id',
                'intelligence_mentor_sessions.account_id',
            ],
            ondelete='CASCADE',
            name='fk_mentor_attachment_session_owner',
        ),
        ForeignKeyConstraint(
            ['batch_id', 'account_id'],
            [
                'intelligence_mentor_attachment_batches.id',
                'intelligence_mentor_attachment_batches.account_id',
            ],
            ondelete='CASCADE',
            name='fk_mentor_attachment_batch_owner',
        ),
        UniqueConstraint(
            'account_id',
            'batch_id',
            'upload_key',
            name='uq_mentor_attachment_upload_replay',
        ),
        CheckConstraint('generation > 0', name='ck_mentor_attachment_generation'),
        CheckConstraint(
            'size_bytes BETWEEN 1 AND 10000000', name='ck_mentor_attachment_size'
        ),
        CheckConstraint(
            "status IN ('uploading', 'processing', 'ready', 'partial', 'failed', 'removed')",
            name='ck_mentor_attachment_status',
        ),
        CheckConstraint(
            '(session_id IS NULL AND message_id IS NULL) OR '
            '(session_id IS NOT NULL AND message_id IS NOT NULL)',
            name='ck_mentor_attachment_binding_pair',
        ),
        CheckConstraint(
            'failure_code IS NULL OR length(failure_code) BETWEEN 1 AND 64',
            name='ck_mentor_attachment_failure_code',
        ),
        UniqueConstraint('object_key', name='uq_mentor_attachment_object_key'),
        Index('ix_mentor_attachment_batch_status', 'batch_id', 'status'),
        Index('ix_mentor_attachment_message', 'session_id', 'message_id'),
        Index('ix_mentor_attachment_claim', 'status', 'claim_expires_at'),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(26), nullable=False)
    batch_id: Mapped[str] = mapped_column(String(26), nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    generation: Mapped[int] = mapped_column(Integer, nullable=False)
    upload_key: Mapped[str] = mapped_column(String(36), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    preview_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    execution_owner: Mapped[str | None] = mapped_column(String(64), nullable=True)
    claim_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    analyzed_pages: Mapped[list[int]] = mapped_column(
        JSON, nullable=False, default=list
    )
    illegible_pages: Mapped[list[int]] = mapped_column(
        JSON, nullable=False, default=list
    )
    uninterpreted_pages: Mapped[list[int]] = mapped_column(
        JSON, nullable=False, default=list
    )
    upload_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
