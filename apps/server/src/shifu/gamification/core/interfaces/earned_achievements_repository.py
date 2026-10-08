from typing import Protocol

from shifu.gamification.core.domain.entities import EarnedAchievement


class EarnedAchievementsRepository(Protocol):
    def find_many_by_account_id(
        self,
        account_id: str,
    ) -> tuple[EarnedAchievement, ...]: ...

    def try_add(self, earned: EarnedAchievement) -> bool:
        """Insert the earned achievement; return False on a unique-constraint conflict.

        Guards against granting the same achievement twice for one account
        under concurrent or duplicate processing.
        """
        ...

    def remove_many_by_account_id(self, account_id: str) -> None:
        """Delete every EarnedAchievement row for one account (account-deletion purge)."""
        ...
