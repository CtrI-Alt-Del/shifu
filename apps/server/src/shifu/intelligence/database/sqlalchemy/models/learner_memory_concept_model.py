from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class LearnerMemoryConceptModel(Model):
    __tablename__ = 'intelligence_learner_memory_concepts'
    __table_args__ = (
        CheckConstraint(
            'position BETWEEN 0 AND 2', name='ck_mentor_memory_concept_position'
        ),
    )

    memory_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('intelligence_learner_memories.id', ondelete='CASCADE'),
        primary_key=True,
    )
    concept_key: Mapped[str] = mapped_column(String(80), primary_key=True)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
