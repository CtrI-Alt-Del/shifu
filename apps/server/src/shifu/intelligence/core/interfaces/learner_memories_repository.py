from datetime import datetime
from typing import Protocol

from shifu.intelligence.core.domain.entities import LearnerMemory
from shifu.intelligence.core.domain.structures import (
    LearnerMemoryConcept,
    LearnerMemoryDetails,
    LearnerMemoryFilter,
    LearnerMemoryOrigin,
)


class LearnerMemoriesRepository(Protocol):
    def lock_account(self, account_id: str) -> datetime | None:
        """Insert the fence row if absent, lock it and return ``deleted_through``."""
        ...

    def advance_fence(self, account_id: str, at: datetime) -> None:
        """Move the fence forward only: ``greatest(coalesce(current, at), at)``."""
        ...

    def find_many(
        self, account_id: str, filter: LearnerMemoryFilter
    ) -> tuple[LearnerMemoryDetails, ...]: ...

    def find_details(
        self, account_id: str, memory_id: str
    ) -> LearnerMemoryDetails | None: ...

    def find_many_by_account(self, account_id: str) -> tuple[LearnerMemory, ...]: ...

    def find_by_id_for_update(
        self, account_id: str, memory_id: str
    ) -> LearnerMemory | None: ...

    def add(
        self,
        memory: LearnerMemory,
        concepts: tuple[LearnerMemoryConcept, ...],
        origin: LearnerMemoryOrigin,
    ) -> None: ...

    def update(
        self, memory: LearnerMemory, concepts: tuple[LearnerMemoryConcept, ...]
    ) -> None: ...

    def add_origin(self, memory_id: str, origin: LearnerMemoryOrigin) -> None: ...

    def remove(self, account_id: str, memory_id: str) -> bool:
        """Remove the memory, its origins and concepts."""
        ...

    def remove_by_account_id(self, account_id: str) -> int:
        """Remove memories, origins, concepts and the fence of the account."""
        ...

    def remove_all(self) -> None:
        """Seed and test maintenance only."""
        ...
