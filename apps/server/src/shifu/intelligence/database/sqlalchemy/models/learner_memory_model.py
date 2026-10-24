from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class LearnerMemoryModel(Model):
    __tablename__ = 'intelligence_learner_memories'
    __table_args__ = (
        CheckConstraint(
            "category IN ('explanation_preference', 'declared_knowledge', "
            "'interest_or_intention', 'recurring_difficulty')",
            name='ck_mentor_memory_category',
        ),
        CheckConstraint(
            'char_length(content) BETWEEN 1 AND 280',
            name='ck_mentor_memory_content_length',
        ),
        CheckConstraint('version >= 1', name='ck_mentor_memory_version'),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(26), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_search: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    last_declared_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


Index(
    'ix_mentor_memory_account_updated',
    LearnerMemoryModel.account_id,
    LearnerMemoryModel.updated_at.desc(),
    LearnerMemoryModel.id,
)
