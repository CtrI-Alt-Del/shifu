from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class ConceptModel(Model):
    __tablename__ = 'curriculum_concepts'
    __table_args__ = (
        Index('ix_curriculum_concept_competency_position', 'competency_id', 'position'),
        UniqueConstraint(
            'competency_id',
            'position',
            name='uq_curriculum_concept_competency_position',
        ),
        CheckConstraint(
            'position >= 1', name='ck_curriculum_concept_position_positive'
        ),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    competency_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('curriculum_competencies.id', ondelete='CASCADE'),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(String(4000), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    observation_criteria: Mapped[str] = mapped_column(String(4000), nullable=False)
    prerequisite_ids: Mapped[object] = mapped_column(JSON, nullable=False)
