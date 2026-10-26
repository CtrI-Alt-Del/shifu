from typing import Protocol


class PlanningWordVectorsProvider(Protocol):
    @property
    def dimension(self) -> int:
        """Return the size of every word vector."""
        ...

    def vectors_of(self, words: tuple[str, ...]) -> dict[str, tuple[float, ...]]:
        """Return the vector of each known word; unknown words are left out."""
        ...
