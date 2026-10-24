from typing import Protocol


class LearnerMemorySimilarityProvider(Protocol):
    def similarity(self, left: str, right: str) -> float:
        """Similarity between two texts in the range 0.0 to 1.0."""
        ...
