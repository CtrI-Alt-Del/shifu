from datetime import datetime
from typing import Protocol
from uuid import UUID

from shifu.identity.core.domain.structures.account_erasure import (
    AccountErasureOverdueParticipant,
    AccountErasureResult,
)


class AccountErasureRepository(Protocol):
    def find_result(self, erasure_id: UUID) -> AccountErasureResult | None: ...

    def find_account_id(self, erasure_id: UUID) -> str | None: ...

    def add(
        self,
        *,
        erasure_id: UUID,
        account_id: str,
        closed_at: datetime,
        due_at: datetime,
        participants: tuple[str, ...],
    ) -> None: ...

    def acknowledge(
        self, erasure_id: UUID, participant: str, *, acknowledged_at: datetime
    ) -> bool: ...

    def find_pending(self, *, limit: int) -> list[UUID]: ...

    def find_overdue_pending_participants(
        self, *, as_of: datetime, limit: int
    ) -> list[AccountErasureOverdueParticipant]: ...

    def remove_completed_before(self, completed_before: datetime, *, limit: int) -> int:
        """Forget completed status records after their recovery retention window."""
        ...
