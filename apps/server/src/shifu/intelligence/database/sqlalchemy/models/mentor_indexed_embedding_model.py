from pgvector.sqlalchemy import Vector
from sqlalchemy import String, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from shifu.shared.database.sqlalchemy.model import Model


class MentorIndexedEmbeddingModel(Model):
    __tablename__ = 'intelligence_mentor_indexed_embeddings'
    __table_args__ = (
        CheckConstraint(
            "corpus IN ('intents', 'answers', 'curriculum')",
            name='ck_mentor_embedding_corpus',
        ),
    )
    version: Mapped[str] = mapped_column(
        String(128),
        ForeignKey(
            'intelligence_mentor_embedding_versions.version', ondelete='CASCADE'
        ),
        primary_key=True,
    )
    corpus: Mapped[str] = mapped_column(String(16), primary_key=True)
    reference_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    variation_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    vector: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
