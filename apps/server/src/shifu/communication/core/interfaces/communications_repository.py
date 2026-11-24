from datetime import datetime
from typing import Protocol

from shifu.communication.core.domain.entities import Communication


class CommunicationsRepository(Protocol):
    def find_by_id(self, communication_id: str) -> Communication | None:
        """Load the row in the caller transaction; mutation paths may lock it."""
        ...

    def find_account_id_by_id(self, communication_id: str) -> str | None:
        """Read the owner without locking before acquiring its activity barrier."""
        ...

    def find_ids_by_account_id(self, account_id: str) -> set[str]:
        """Find Communication rows owned by an account."""
        ...

    def remove_many_by_ids(self, communication_ids: set[str]) -> int:
        """Remove selected Communication rows."""
        ...

    def find_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> Communication | None: ...

    def find_pending_due(
        self,
        *,
        now: datetime,
        limit: int,
    ) -> list[Communication]:
        """Return pending communications eligible for delivery."""
        ...

    def add(self, communication: Communication) -> None: ...

    def add_many(self, communications: list[Communication]) -> None: ...

    def update(self, communication: Communication) -> None: ...

    def remove_all(self) -> None: ...
