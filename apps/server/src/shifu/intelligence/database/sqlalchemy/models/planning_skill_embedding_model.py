from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class PlanningSkillEmbeddingModel(Model):
    __tablename__ = 'intelligence_planning_skill_embeddings'
    version: Mapped[str] = mapped_column(
        String(128),
        ForeignKey(
            'intelligence_planning_embedding_versions.version', ondelete='CASCADE'
        ),
        primary_key=True,
    )
    skill_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    vector: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
