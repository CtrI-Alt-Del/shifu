from shifu.gamification.core.domain.errors import GamificationProfileNotFoundError
from shifu.gamification.core.domain.streak_reminder_settings_of import (
    streak_reminder_settings_of,
)
from shifu.gamification.core.domain.structures import StreakReminderSettings
from shifu.gamification.core.interfaces import GamificationDatabase


class GetStreakReminderSettingsUseCase:
    """Read the account's reminder hour and invite state."""

    def __init__(self, database: GamificationDatabase) -> None:
        self._database = database

    def execute(self, account_id: str) -> StreakReminderSettings:
        with self._database.transaction() as repositories:
            profile = repositories.profiles.find_by_account_id(account_id)
            if profile is None:
                raise GamificationProfileNotFoundError
            return streak_reminder_settings_of(profile)
