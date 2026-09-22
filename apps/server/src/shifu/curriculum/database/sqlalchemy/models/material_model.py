from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class MaterialModel(Model):
    __tablename__ = 'curriculum_materials'
    __table_args__ = (Index('ix_curriculum_material_skill_id', 'skill_id'),)

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    skill_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('curriculum_skills.id', ondelete='CASCADE'),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    content: Mapped[str] = mapped_column(String(20000), nullable=False)
    material_type: Mapped[str] = mapped_column(String(40), nullable=False)
