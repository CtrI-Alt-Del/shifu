from typing import Protocol
from uuid import UUID


class AccountErasureAcknowledgementProvider(Protocol):
    def acknowledge(self, erasure_id: UUID, participant: str) -> None:
        """Idempotently acknowledge one participant's completed purge."""
        ...
