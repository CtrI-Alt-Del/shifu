from datetime import date, datetime
from typing import Protocol

from shifu.intelligence.core.domain.entities.ai_quota_month import AiQuotaMonth


class AiQuotaMonthsRepository(Protocol):
    def ensure_and_lock(
        self, account_id: str, month: date, limit_units: int, now: datetime
    ) -> AiQuotaMonth:
        """Create the month when absent, then lock and return it.

        Only admission and registration call this; a month keeps the limit
        copied when its row was created.
        """
        ...

    def lock_existing(self, account_id: str, month: date) -> AiQuotaMonth | None:
        """Lock a month that already exists; never create one (charge and refund)."""
        ...

    def find_by_account_and_month(
        self, account_id: str, month: date
    ) -> AiQuotaMonth | None: ...

    def update(self, month: AiQuotaMonth) -> None: ...

    def lock_by_account_id(self, account_id: str) -> None:
        """Lock every month of the account so a purge cannot interleave with charges."""
        ...

    def remove_by_account_id(self, account_id: str) -> int: ...
