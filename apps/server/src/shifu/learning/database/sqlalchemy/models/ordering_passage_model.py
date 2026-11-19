from sqlalchemy import CheckConstraint, ForeignKey, Index, JSON, String, text
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class OrderingPassageModel(Model):
    __tablename__ = 'learning_ordering_passages'
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'consumed')",
            name='ck_learning_ordering_passage_status',
        ),
        Index(
            'uq_learning_ordering_passage_experience_activity_key',
            'skill_experience_id',
            'activity_id',
            'passage_key',
            unique=True,
        ),
        Index(
            'uq_learning_ordering_passage_active_experience_activity',
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
    passage_key: Mapped[str] = mapped_column(String(36), nullable=False)
    activity_revision: Mapped[str] = mapped_column(String(128), nullable=False)
    grading_snapshot: Mapped[object] = mapped_column(JSON, nullable=False)
    verified_orderings: Mapped[object] = mapped_column(JSON, nullable=False)
    schema_version: Mapped[int] = mapped_column(nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
