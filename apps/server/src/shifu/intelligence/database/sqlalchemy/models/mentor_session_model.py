from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class MentorSessionModel(Model):
    __tablename__ = 'intelligence_mentor_sessions'
    __table_args__ = (
        UniqueConstraint('account_id', 'submission_key', name='uq_mentor_submission'),
        Index(
            'ix_mentor_account_activity',
            'account_id',
            'last_activity_at',
            'id',
        ),
        CheckConstraint(
            '(deleted_at IS NULL AND title IS NOT NULL AND title_search IS NOT NULL '
            'AND created_at IS NOT NULL AND updated_at IS NOT NULL '
            'AND last_activity_at IS NOT NULL AND content_fingerprint IS NOT NULL) '
            'OR (deleted_at IS NOT NULL AND title IS NULL AND title_search IS NULL '
            'AND created_at IS NULL AND updated_at IS NULL '
            'AND last_activity_at IS NULL AND content_fingerprint IS NULL)',
            name='ck_mentor_session_active_or_tombstone',
        ),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(26), nullable=False)
    submission_key: Mapped[str] = mapped_column(String(36), nullable=False)
    content_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    title_search: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
