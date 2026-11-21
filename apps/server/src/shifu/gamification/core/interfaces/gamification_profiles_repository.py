from datetime import date
from typing import Protocol

from shifu.gamification.core.domain.entities import GamificationProfile


class GamificationProfilesRepository(Protocol):
    def find_by_account_id(self, account_id: str) -> GamificationProfile | None:
        """Read the profile without locking it. Use it only for read-only paths."""
        ...

    def find_by_account_id_for_update(
        self, account_id: str
    ) -> GamificationProfile | None:
        """Read the profile and hold its row lock until the transaction ends.

        Every read-modify-write of the profile loads it here, so concurrent
        writers serialize and the later one reads the committed values.
        """
        ...

    def add(self, profile: GamificationProfile) -> None: ...

    def update(self, profile: GamificationProfile) -> None: ...

    def remove(self, profile: GamificationProfile) -> None: ...

    def find_many_reminder_candidates(
        self,
        *,
        practiced_since: date,
        after_account_id: str | None,
        limit: int,
    ) -> tuple[GamificationProfile, ...]:
        """Profiles whose latest practice date is on or after `practiced_since`.

        Ordered by `account_id` and strictly after `after_account_id` when it is
        given, so a caller can walk the whole set in bounded pages.
        """
        ...
