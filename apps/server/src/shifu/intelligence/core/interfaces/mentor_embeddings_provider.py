from typing import Protocol


class MentorEmbeddingsProvider(Protocol):
    def embed_queries(
        self, texts: tuple[str, ...]
    ) -> tuple[tuple[float, ...], ...]: ...
    def embed_passages(
        self, texts: tuple[str, ...]
    ) -> tuple[tuple[float, ...], ...]: ...
