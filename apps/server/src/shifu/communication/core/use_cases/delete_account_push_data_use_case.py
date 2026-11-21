from shifu.communication.core.interfaces import CommunicationDatabase
from shifu.shared.core.interfaces import ClockProvider


class DeleteAccountPushDataUseCase:
    """Cancel and erase every push record that belongs to a deleted account."""

    def __init__(
        self,
        database: CommunicationDatabase,
        clock_provider: ClockProvider,
    ) -> None:
        self._database = database
        self._clock_provider = clock_provider

    def execute(self, account_id: str) -> None:
        with self._database.transaction() as repositories:
            now = self._clock_provider.now()
            for (
                reminder
            ) in repositories.streak_reminders.find_many_pending_by_account_id(
                account_id
            ):
                reminder.cancel(now)
                repositories.streak_reminders.update(reminder)

            # Deliveries leave with their reminders through the foreign key cascade.
            repositories.streak_reminders.remove_many_by_account_id(account_id)
            repositories.push_subscriptions.remove_many_by_account_id(account_id)
            repositories.streak_reminder_preferences.remove_by_account_id(account_id)
