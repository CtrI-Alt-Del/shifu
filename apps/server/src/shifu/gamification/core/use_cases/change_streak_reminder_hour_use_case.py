from datetime import datetime

from shifu.gamification.core.domain.errors import GamificationProfileNotFoundError
from shifu.gamification.core.domain.streak_reminder_settings_of import (
    streak_reminder_settings_of,
)
from shifu.gamification.core.domain.structures import StreakReminderSettings
from shifu.gamification.core.interfaces import GamificationDatabase


class ChangeStreakReminderHourUseCase:
    """Store a new whole reminder hour, rejecting hours outside 06 to 22.

    The hour applies from the next slot evaluation, so a change made before the
    new hour's slot starts still takes effect the same day.
    """

    def __init__(self, database: GamificationDatabase) -> None:
        self._database = database

    def execute(
        self, account_id: str, hour: int, *, now: datetime
    ) -> StreakReminderSettings:
        with self._database.transaction() as repositories:
            profile = repositories.profiles.find_by_account_id_for_update(account_id)
            if profile is None:
                raise GamificationProfileNotFoundError
            profile.change_reminder_hour(hour, updated_at=now)
            repositories.profiles.update(profile)
            return streak_reminder_settings_of(profile)
