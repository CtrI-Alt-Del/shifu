from typing import Protocol

from shifu.intelligence.core.domain.structures.planning_embedding_match import (
    PlanningEmbeddingMatch,
)
from shifu.intelligence.core.domain.structures.planning_indexed_embedding import (
    PlanningIndexedEmbedding,
)


class PlanningEmbeddingsRepository(Protocol):
    def prepare_version(
        self, version: str, vectors: tuple[PlanningIndexedEmbedding, ...]
    ) -> None:
        """Write the complete Skill corpus under an inactive version."""
        ...

    def activate_version(self, version: str) -> None:
        """Make the version the only active one."""
        ...

    def find_active_version(self) -> str | None: ...

    def find_nearest(
        self,
        version: str,
        query: tuple[float, ...],
        eligible_skill_ids: tuple[str, ...],
        limit: int,
    ) -> tuple[PlanningEmbeddingMatch, ...]:
        """Return eligible Skills ordered by similarity, then Skill id."""
        ...
