from shifu.intelligence.core.domain.structures import (
    PlanningEmbeddingMatch,
    PlanningIndexedEmbedding,
)
from shifu.intelligence.core.interfaces import IntelligenceDatabase


class PlanningEmbeddingsDatabaseRepository:
    """Open one Intelligence transaction per index operation."""

    def __init__(self, database: IntelligenceDatabase) -> None:
        self._database: IntelligenceDatabase = database

    def prepare_version(
        self, version: str, vectors: tuple[PlanningIndexedEmbedding, ...]
    ) -> None:
        with self._database.transaction() as repositories:
            repositories.planning_embeddings.prepare_version(version, vectors)

    def activate_version(self, version: str) -> None:
        with self._database.transaction() as repositories:
            repositories.planning_embeddings.activate_version(version)

    def find_active_version(self) -> str | None:
        with self._database.transaction() as repositories:
            return repositories.planning_embeddings.find_active_version()

    def find_nearest(
        self,
        version: str,
        query: tuple[float, ...],
        eligible_skill_ids: tuple[str, ...],
        limit: int,
    ) -> tuple[PlanningEmbeddingMatch, ...]:
        with self._database.transaction() as repositories:
            return repositories.planning_embeddings.find_nearest(
                version, query, eligible_skill_ids, limit
            )
