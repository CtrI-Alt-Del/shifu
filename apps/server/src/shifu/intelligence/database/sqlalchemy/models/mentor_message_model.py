from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class MentorMessageModel(Model):
    __tablename__ = 'intelligence_mentor_messages'
    __table_args__ = (
        UniqueConstraint(
            'in_reply_to_message_id',
            name='uq_mentor_response_per_learner_message',
        ),
        UniqueConstraint('session_id', 'id', name='uq_mentor_message_session_id'),
        ForeignKeyConstraint(
            ['session_id', 'in_reply_to_message_id'],
            [
                'intelligence_mentor_messages.session_id',
                'intelligence_mentor_messages.id',
            ],
            ondelete='CASCADE',
            name='fk_mentor_message_reply_same_session',
        ),
        CheckConstraint(
            "(role = 'learner' AND in_reply_to_message_id IS NULL) OR "
            "(role = 'mentor' AND in_reply_to_message_id IS NOT NULL)",
            name='ck_mentor_message_role_reply',
        ),
        Index('ix_mentor_message_history', 'session_id', 'created_at', 'id'),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('intelligence_mentor_sessions.id', ondelete='CASCADE'),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    in_reply_to_message_id: Mapped[str | None] = mapped_column(
        String(26),
        nullable=True,
    )
