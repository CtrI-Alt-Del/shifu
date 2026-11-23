from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class PracticePhotoModel(Model):
    __tablename__ = 'learning_practice_photos'
    __table_args__ = (
        CheckConstraint(
            "state IN ('uploading', 'ready', 'failed', 'removed')",
            name='ck_learning_practice_photo_state',
        ),
        CheckConstraint(
            "(owner_kind = 'draft' AND draft_id IS NOT NULL AND attempt_id IS NULL) "
            "OR (owner_kind = 'attempt' AND draft_id IS NULL AND attempt_id IS NOT NULL)",
            name='ck_learning_practice_photo_owner',
        ),
        CheckConstraint('size_bytes > 0', name='ck_learning_practice_photo_size'),
        Index('ix_learning_practice_photo_draft', 'draft_id'),
        Index('ix_learning_practice_photo_attempt', 'attempt_id'),
        Index(
            'uq_learning_practice_photo_draft_upload_key',
            'draft_id',
            'upload_key',
            unique=True,
            postgresql_where=text('draft_id IS NOT NULL'),
            sqlite_where=text('draft_id IS NOT NULL'),
        ),
        Index(
            'uq_learning_practice_photo_draft_live_record',
            'draft_id',
            'record_key',
            unique=True,
            postgresql_where=text("draft_id IS NOT NULL AND state <> 'removed'"),
            sqlite_where=text("draft_id IS NOT NULL AND state <> 'removed'"),
        ),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    owner_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    draft_id: Mapped[str | None] = mapped_column(
        String(26),
        ForeignKey('learning_practice_drafts.id', ondelete='CASCADE'),
        nullable=True,
    )
    attempt_id: Mapped[str | None] = mapped_column(
        String(26),
        ForeignKey('learning_activity_attempts.id', ondelete='CASCADE'),
        nullable=True,
    )
    record_key: Mapped[str] = mapped_column(String(100), nullable=False)
    object_key: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(40), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    upload_key: Mapped[str] = mapped_column(String(36), nullable=False)
    removal_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
