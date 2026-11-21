from typing import Protocol

from shifu.communication.core.domain.entities import StreakReminderPreference


class StreakReminderPreferencesRepository(Protocol):
    def find_by_account_id(
        self, account_id: str
    ) -> StreakReminderPreference | None: ...

    def add(self, preference: StreakReminderPreference) -> None: ...

    def try_add(self, preference: StreakReminderPreference) -> bool:
        """Insert the preference; return False when the account already has one."""
        ...

    def update(self, preference: StreakReminderPreference) -> None: ...

    def remove_by_account_id(self, account_id: str) -> None: ...
