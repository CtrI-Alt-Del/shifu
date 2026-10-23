from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class LearnerMemoryOriginModel(Model):
    __tablename__ = 'intelligence_learner_memory_origins'
    __table_args__ = (
        Index(
            'uq_mentor_memory_origin_message',
            'memory_id',
            'message_id',
            unique=True,
            postgresql_where=text('message_id IS NOT NULL'),
        ),
        Index('ix_mentor_memory_origin_memory', 'memory_id', 'declared_at'),
        Index('ix_mentor_memory_origin_message', 'message_id'),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    memory_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('intelligence_learner_memories.id', ondelete='CASCADE'),
        nullable=False,
    )
    session_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('intelligence_mentor_sessions.id'),
        nullable=False,
    )
    message_id: Mapped[str | None] = mapped_column(
        String(26),
        ForeignKey('intelligence_mentor_messages.id', ondelete='SET NULL'),
        nullable=True,
    )
    declared_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
