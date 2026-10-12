from typing import Protocol
from shifu.intelligence.core.domain.structures import (
    MentorIndexedEmbedding,
    MentorEmbeddingMatch,
)


class MentorEmbeddingsRepository(Protocol):
    def prepare_version(
        self, version: str, vectors: tuple[MentorIndexedEmbedding, ...]
    ) -> None: ...
    def activate_version(self, version: str) -> None: ...
    def find_nearest(
        self,
        corpus: str,
        version: str,
        query: tuple[float, ...],
        eligible_references: tuple[str, ...],
    ) -> tuple[MentorEmbeddingMatch, ...]: ...
