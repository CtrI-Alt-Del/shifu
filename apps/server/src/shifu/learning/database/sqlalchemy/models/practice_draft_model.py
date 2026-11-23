from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class PracticeDraftModel(Model):
    __tablename__ = 'learning_practice_drafts'
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'consumed')",
            name='ck_learning_practice_draft_status',
        ),
        CheckConstraint('revision >= 0', name='ck_learning_practice_draft_revision'),
        Index(
            'uq_learning_practice_draft_active_experience_activity',
            'skill_experience_id',
            'activity_id',
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    skill_experience_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('learning_skill_experiences.id', ondelete='CASCADE'),
        nullable=False,
    )
    activity_id: Mapped[str] = mapped_column(String(26), nullable=False)
    reflection: Mapped[str] = mapped_column(Text, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
