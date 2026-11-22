from typing import Protocol

from shifu.learning.core.domain.entities import PracticeDraft


class PracticeDraftsRepository(Protocol):
    def find_active(
        self, skill_experience_id: str, activity_id: str
    ) -> PracticeDraft | None: ...

    def find_active_for_update(
        self, skill_experience_id: str, activity_id: str
    ) -> PracticeDraft | None:
        """Return the active draft while holding a row lock until the transaction ends."""
        ...

    def find_many_by_skill_experience_id(
        self, skill_experience_id: str
    ) -> list[PracticeDraft]: ...

    def add(self, draft: PracticeDraft) -> None: ...

    def update(self, draft: PracticeDraft) -> None: ...

    def remove(self, draft_id: str) -> None: ...
