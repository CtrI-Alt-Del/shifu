from datetime import datetime
from typing import Protocol


class AccountBrowserCapabilitiesRepository(Protocol):
    def add(
        self, *, account_id: str, capability_hash: str, created_at: datetime
    ) -> None: ...

    def find_status_by_hash(self, capability_hash: str) -> str | None: ...

    def revoke_by_account_id(self, account_id: str) -> int: ...

    def remove_by_account_id(self, account_id: str) -> int: ...
