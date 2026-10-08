from typing import Protocol

from shifu.gamification.core.domain.entities import RewardedMilestone
from shifu.gamification.core.domain.enums import MilestoneKind


class RewardedMilestonesRepository(Protocol):
    def count_by_account_id_and_kind(
        self,
        account_id: str,
        kind: MilestoneKind,
    ) -> int: ...

    def try_add(self, milestone: RewardedMilestone) -> bool:
        """Insert the milestone; return False on a unique-constraint conflict.

        This is the sole idempotency gate for Learning-fact recognition: it
        never raises on a duplicate, it reports the conflict as `False`.
        """
        ...

    def remove_many_by_account_id(self, account_id: str) -> None:
        """Delete every RewardedMilestone row for one account (account-deletion purge)."""
        ...
