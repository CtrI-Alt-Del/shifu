from datetime import date
from typing import Protocol

from shifu.gamification.core.domain.entities import PracticeDay


class PracticeDaysRepository(Protocol):
    def try_add(self, practice_day: PracticeDay) -> bool:
        """Insert one practice day.

        Return `False` when the account already has a day for that local
        date. The uniqueness of `(account_id, practice_date)` is what makes
        several practices on one day count once and a redelivered fact
        harmless.
        """
        ...

    def find_many_dates_by_account_id(self, account_id: str) -> tuple[date, ...]:
        """Every recognized local date for one account, ascending."""
        ...

    def remove_many_by_account_id(self, account_id: str) -> None:
        """Delete every PracticeDay row for one account (account-deletion purge)."""
        ...
