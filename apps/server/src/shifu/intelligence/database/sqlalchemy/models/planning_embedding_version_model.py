from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class PlanningEmbeddingVersionModel(Model):
    __tablename__ = 'intelligence_planning_embedding_versions'
    version: Mapped[str] = mapped_column(String(128), primary_key=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
