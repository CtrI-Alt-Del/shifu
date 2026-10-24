from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class LearnerMemoryChangeModel(Model):
    __tablename__ = 'intelligence_learner_memory_changes'
    __table_args__ = (
        CheckConstraint(
            "kind IN ('created', 'updated')", name='ck_mentor_memory_change_kind'
        ),
        CheckConstraint(
            "category IN ('explanation_preference', 'declared_knowledge', "
            "'interest_or_intention', 'recurring_difficulty')",
            name='ck_mentor_memory_change_category',
        ),
        CheckConstraint(
            'memory_id IS NOT NULL OR (content IS NULL AND previous_content IS NULL)',
            name='ck_mentor_memory_change_erased',
        ),
        CheckConstraint(
            "kind <> 'created' OR previous_content IS NULL",
            name='ck_mentor_memory_change_created',
        ),
        Index('ix_mentor_memory_change_session', 'session_id', 'created_at'),
        Index('ix_mentor_memory_change_memory', 'memory_id'),
        Index('ix_mentor_memory_change_message', 'message_id'),
        Index('ix_mentor_memory_change_account', 'account_id'),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(26), nullable=False)
    memory_id: Mapped[str | None] = mapped_column(
        String(26),
        ForeignKey('intelligence_learner_memories.id', ondelete='SET NULL'),
        nullable=True,
    )
    session_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('intelligence_mentor_sessions.id'),
        nullable=False,
    )
    message_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('intelligence_mentor_messages.id', ondelete='CASCADE'),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
