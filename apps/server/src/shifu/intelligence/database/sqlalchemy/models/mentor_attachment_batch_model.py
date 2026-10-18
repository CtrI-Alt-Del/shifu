from datetime import datetime

from sqlalchemy import (
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


class MentorAttachmentBatchModel(Model):
    __tablename__ = 'intelligence_mentor_attachment_batches'
    __table_args__ = (
        ForeignKeyConstraint(
            ['session_id', 'account_id'],
            [
                'intelligence_mentor_sessions.id',
                'intelligence_mentor_sessions.account_id',
            ],
            ondelete='CASCADE',
            name='fk_mentor_attachment_batch_session_owner',
        ),
        CheckConstraint('generation > 0', name='ck_mentor_attachment_batch_generation'),
        Index('ix_mentor_attachment_batch_expiry', 'expires_at', 'id'),
        Index('ix_mentor_attachment_batch_owner', 'account_id', 'session_id'),
        UniqueConstraint('id', 'account_id', name='uq_mentor_attachment_batch_owner'),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(26), nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    generation: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    consumed_by_message_id: Mapped[str | None] = mapped_column(
        String(26), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
