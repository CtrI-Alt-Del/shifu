from typing import Protocol

from shifu.intelligence.core.domain.entities import LearnerMemoryChange
from shifu.intelligence.core.domain.structures import MentorConversationMemoryItem


class LearnerMemoryChangesRepository(Protocol):
    def add(self, change: LearnerMemoryChange) -> None: ...

    def find_items_by_session(
        self, account_id: str, session_id: str
    ) -> tuple[MentorConversationMemoryItem, ...]: ...

    def erase_by_memory_id(self, account_id: str, memory_id: str) -> None:
        """Privacy erasure scoped to the owner: texts become null and the link is cut."""
        ...

    def remove_by_session_id(self, session_id: str) -> None: ...

    def remove_by_account_id(self, account_id: str) -> int: ...

    def remove_all(self) -> None:
        """Seed and test maintenance only."""
        ...
