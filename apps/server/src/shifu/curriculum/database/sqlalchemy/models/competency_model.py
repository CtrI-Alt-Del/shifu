from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class CompetencyModel(Model):
    __tablename__ = 'curriculum_competencies'
    __table_args__ = (
        Index('ix_curriculum_competency_skill_position', 'skill_id', 'position'),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    skill_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('curriculum_skills.id', ondelete='CASCADE'),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(String(4000), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
