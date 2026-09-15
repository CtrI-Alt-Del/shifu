from datetime import datetime
from typing import Protocol

from shifu.identity.core.domain.entities import Account


class AccountsRepository(Protocol):
    def find_by_id(self, account_id: str) -> Account | None: ...

    def find_non_deleted_by_email(self, email: str) -> Account | None: ...

    def find_many_pending_created_before(
        self,
        created_before: datetime,
    ) -> list[Account]:
        """Find pending accounts using a timezone-aware UTC cutoff."""
        ...

    def add(self, account: Account) -> None: ...

    def replace(self, account: Account) -> None: ...
