import math
from sqlalchemy import select, delete, update
from sqlalchemy.orm import Session

from shifu.intelligence.core.domain.structures import (
    MentorIndexedEmbedding,
    MentorEmbeddingMatch,
)
from shifu.intelligence.database.sqlalchemy.models.mentor_embedding_version_model import (
    MentorEmbeddingVersionModel,
)
from shifu.intelligence.database.sqlalchemy.models.mentor_indexed_embedding_model import (
    MentorIndexedEmbeddingModel,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError


class SqlalchemyMentorEmbeddingsRepository:
    def __init__(self, session: Session) -> None:
        self._session: Session = session

    def prepare_version(
        self, version: str, vectors: tuple[MentorIndexedEmbedding, ...]
    ) -> None:
        if not version or not vectors:
            raise ValueError('Index version and complete corpus required')
        identities = {
            (item.corpus, item.reference_id, item.variation_key) for item in vectors
        }
        if len(identities) != len(vectors):
            raise ValueError('Duplicate embedding identity')
        for item in vectors:
            self._validate_vector(item.vector)
            if item.corpus not in ('intents', 'answers', 'curriculum'):
                raise ValueError('Invalid corpus')
        existing = self._session.get(MentorEmbeddingVersionModel, version)
        if existing is not None and existing.active:
            raise ValueError('Active immutable index cannot be replaced')
        if existing is None:
            self._session.add(
                MentorEmbeddingVersionModel(version=version, active=False)
            )
            self._session.flush()
        self._session.execute(
            delete(MentorIndexedEmbeddingModel).where(
                MentorIndexedEmbeddingModel.version == version
            )
        )
        self._session.add_all(
            [
                MentorIndexedEmbeddingModel(
                    version=version,
                    corpus=item.corpus,
                    reference_id=item.reference_id,
                    variation_key=item.variation_key,
                    vector=list(item.vector),
                )
                for item in vectors
            ]
        )
        self._session.flush()

    def activate_version(self, version: str) -> None:
        existing = self._session.scalar(
            select(MentorEmbeddingVersionModel)
            .where(MentorEmbeddingVersionModel.version == version)
            .with_for_update()
        )
        if existing is None:
            raise ServiceUnavailableError
        corpus = set(
            self._session.scalars(
                select(MentorIndexedEmbeddingModel.corpus)
                .where(MentorIndexedEmbeddingModel.version == version)
                .distinct()
            )
        )
        if not {'intents', 'answers'}.issubset(corpus):
            raise ServiceUnavailableError
        self._session.execute(update(MentorEmbeddingVersionModel).values(active=False))
        existing.active = True
        self._session.flush()

    def find_nearest(
        self,
        corpus: str,
        version: str,
        query: tuple[float, ...],
        eligible_references: tuple[str, ...],
    ) -> tuple[MentorEmbeddingMatch, ...]:
        self._validate_vector(query)
        existing = self._session.get(MentorEmbeddingVersionModel, version)
        if existing is None or not existing.active:
            raise ServiceUnavailableError
        if not eligible_references:
            return ()
        distance = MentorIndexedEmbeddingModel.vector.cosine_distance(list(query))
        rows = self._session.execute(
            select(
                MentorIndexedEmbeddingModel.reference_id,
                MentorIndexedEmbeddingModel.variation_key,
                distance.label('distance'),
            )
            .where(
                MentorIndexedEmbeddingModel.corpus == corpus,
                MentorIndexedEmbeddingModel.version == version,
                MentorIndexedEmbeddingModel.reference_id.in_(eligible_references),
            )
            .order_by(
                distance,
                MentorIndexedEmbeddingModel.reference_id,
                MentorIndexedEmbeddingModel.variation_key,
            )
        ).all()
        return tuple(
            MentorEmbeddingMatch(
                reference_id=row.reference_id,
                variation_key=row.variation_key,
                similarity=1.0 - float(row.distance),
            )
            for row in rows
        )

    @staticmethod
    def _validate_vector(vector: tuple[float, ...]) -> None:
        if len(vector) != 384 or not all(math.isfinite(value) for value in vector):
            raise ValueError('Invalid embedding dimensions or values')
        norm = math.sqrt(sum(value * value for value in vector))
        if not math.isclose(norm, 1.0, rel_tol=1e-4, abs_tol=1e-4):
            raise ValueError('Embedding must be normalized')
