from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class SkillModel(Model):
    __tablename__ = 'curriculum_skills'

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(4000), nullable=False)
    initial_diagnostic_activity_ids: Mapped[object] = mapped_column(
        JSON, nullable=False, default=list
    )
