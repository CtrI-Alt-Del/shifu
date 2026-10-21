from typing import Protocol

from shifu.shared.core.domain.structures import MentorCatalogEntry


class MentorCatalogProvider(Protocol):
    def read_projection(self) -> tuple[MentorCatalogEntry, ...]: ...

    def is_diagnostic_activity(
        self,
        skill_id: str,
        competency_id: str | None,
        activity_id: str,
    ) -> bool: ...

    def search(
        self,
        account_id: str,
        query: str,
        eligible_references: tuple[str, ...],
    ) -> tuple[MentorCatalogEntry, ...]: ...
