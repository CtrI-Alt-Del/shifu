from datetime import datetime
from typing import Protocol

from shifu.communication.core.domain.entities import Communication


class CommunicationsRepository(Protocol):
    def find_by_id(self, communication_id: str) -> Communication | None: ...

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
