from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.base import Model


class CurriculumSequenceModel(Model):
    __tablename__ = 'curriculum_sequences'

    competency_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('curriculum_competencies.id', ondelete='CASCADE'),
        primary_key=True,
    )
    items: Mapped[object] = mapped_column(JSON, nullable=False)
