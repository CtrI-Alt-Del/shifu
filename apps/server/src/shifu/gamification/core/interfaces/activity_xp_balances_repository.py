from typing import Protocol

from shifu.gamification.core.domain.entities import ActivityXpBalance


class ActivityXpBalancesRepository(Protocol):
    def find_by_account_id_and_activity_id(
        self, account_id: str, activity_id: str
    ) -> ActivityXpBalance | None:
        """The account's accumulator for one Activity, locked for the open transaction."""
        ...

    def add(self, balance: ActivityXpBalance) -> None: ...

    def update(self, balance: ActivityXpBalance) -> None: ...

    def remove_many_by_account_id(self, account_id: str) -> None:
        """Delete every ActivityXpBalance row for one account (account-deletion purge)."""
        ...
