from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.base import Base


class SkillModel(Base):
    __tablename__ = 'curriculum_skills'

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(4000), nullable=False)
