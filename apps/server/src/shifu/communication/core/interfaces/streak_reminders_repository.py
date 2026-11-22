from datetime import date, datetime
from typing import Protocol

from shifu.communication.core.domain.entities import StreakReminder


class StreakRemindersRepository(Protocol):
    def find_by_id_for_update(self, reminder_id: str) -> StreakReminder | None: ...

    def find_by_account_id_and_local_date(
        self, account_id: str, local_date: date
    ) -> StreakReminder | None: ...

    def try_add(self, reminder: StreakReminder) -> bool:
        """Insert the reminder; return False on an (account_id, local_date) conflict."""
        ...

    def update(self, reminder: StreakReminder) -> None: ...

    def find_many_pending_by_account_id(
        self, account_id: str
    ) -> tuple[StreakReminder, ...]: ...

    def remove_many_by_account_id(self, account_id: str) -> None: ...

    def find_many_open_by_account_id(
        self, account_id: str, *, now: datetime
    ) -> tuple[StreakReminder, ...]:
        """Return reminders of any status whose local day has not ended at `now`."""
        ...

    def remove(self, reminder: StreakReminder) -> None: ...
