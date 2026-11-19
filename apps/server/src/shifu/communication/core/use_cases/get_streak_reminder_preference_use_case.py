from shifu.communication.core.interfaces import CommunicationDatabase


class GetStreakReminderPreferenceUseCase:
    """Read the account-wide streak reminder switch; absent means off."""

    def __init__(self, database: CommunicationDatabase) -> None:
        self._database = database

    def execute(self, account_id: str) -> bool:
        with self._database.transaction() as repositories:
            preference = repositories.streak_reminder_preferences.find_by_account_id(
                account_id
            )
            return preference is not None and preference.enabled
