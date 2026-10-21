from shifu.intelligence.core.domain.structures import (
    MentorEmbeddingMatch,
    MentorIndexedEmbedding,
)
from shifu.intelligence.core.interfaces import IntelligenceDatabase


class MentorEmbeddingsDatabaseRepository:
    def __init__(self, database: IntelligenceDatabase) -> None:
        self._database: IntelligenceDatabase = database

    def prepare_version(
        self, version: str, vectors: tuple[MentorIndexedEmbedding, ...]
    ) -> None:
        with self._database.transaction() as repositories:
            repositories.mentor_embeddings.prepare_version(version, vectors)

    def activate_version(self, version: str) -> None:
        with self._database.transaction() as repositories:
            repositories.mentor_embeddings.activate_version(version)

    def find_nearest(
        self,
        corpus: str,
        version: str,
        query: tuple[float, ...],
        eligible_references: tuple[str, ...],
    ) -> tuple[MentorEmbeddingMatch, ...]:
        with self._database.transaction() as repositories:
            return repositories.mentor_embeddings.find_nearest(
                corpus, version, query, eligible_references
            )
