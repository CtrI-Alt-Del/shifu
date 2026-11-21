from shifu.communication.core.interfaces import CommunicationDatabase
from shifu.shared.core.interfaces import ClockProvider


class ClearCurrentStreakRemindersUseCase:
    """Remove the reminder of the learner's current local day, whatever its status.

    Only the local demonstration command calls this, so every run can deliver again.
    The scheduled flow never clears a reminder. A retry waiting for a cleared reminder
    finds nothing and stops.
    """

    def __init__(
        self,
        database: CommunicationDatabase,
        clock_provider: ClockProvider,
    ) -> None:
        self._database = database
        self._clock_provider = clock_provider

    def execute(self, account_id: str) -> int:
        with self._database.transaction() as repositories:
            now = self._clock_provider.now()
            reminders = repositories.streak_reminders.find_many_open_by_account_id(
                account_id,
                now=now,
            )
            for reminder in reminders:
                repositories.streak_reminders.remove(reminder)
            return len(reminders)
