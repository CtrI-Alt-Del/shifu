from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.base import Base


class SkillFoundationModel(Base):
    __tablename__ = 'curriculum_skill_foundations'

    skill_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('curriculum_skills.id', ondelete='CASCADE'),
        primary_key=True,
    )
    foundation_skill_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('curriculum_skills.id', ondelete='CASCADE'),
        primary_key=True,
    )
