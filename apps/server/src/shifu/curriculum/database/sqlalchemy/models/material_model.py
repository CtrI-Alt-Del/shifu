from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.base import Model


class MaterialModel(Model):
    __tablename__ = 'curriculum_materials'

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    skill_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('curriculum_skills.id', ondelete='CASCADE'),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    content: Mapped[str] = mapped_column(String(20000), nullable=False)
    material_type: Mapped[str] = mapped_column(String(40), nullable=False)
