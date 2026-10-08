from typing import Protocol

from shifu.gamification.core.domain.entities import XpGrant


class XpGrantsRepository(Protocol):
    def add(self, grant: XpGrant) -> None: ...

    def remove_many_by_account_id(self, account_id: str) -> None:
        """Delete every XpGrant row for one account (account-deletion purge)."""
        ...
