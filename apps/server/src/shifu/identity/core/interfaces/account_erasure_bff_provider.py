from typing import Protocol
from uuid import UUID


class AccountErasureBffProvider(Protocol):
    def close_technical_identity(self, account_id: str, erasure_id: UUID) -> None:
        """Idempotently close the Better Auth identity for a pending erasure."""
        ...
