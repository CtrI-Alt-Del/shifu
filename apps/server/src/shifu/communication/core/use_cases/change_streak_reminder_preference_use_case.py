from datetime import datetime

from shifu.communication.core.domain.entities import StreakReminderPreference
from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.communication.core.interfaces import CommunicationDatabase


class ChangeStreakReminderPreferenceUseCase:
    """Turn the account-wide streak reminder switch on or off."""

    def __init__(self, database: CommunicationDatabase) -> None:
        self._database = database

    def execute(self, account_id: str, *, enabled: bool, now: datetime) -> bool:
        with self._database.transaction() as repositories:
            preference = repositories.streak_reminder_preferences.find_by_account_id(
                account_id
            )
            if preference is None:
                created = StreakReminderPreference.create(
                    account_id=account_id,
                    enabled=enabled,
                    now=now,
                )
                if repositories.streak_reminder_preferences.try_add(created):
                    return enabled

                # A concurrent first change won; apply this change on top of it.
                preference = (
                    repositories.streak_reminder_preferences.find_by_account_id(
                        account_id
                    )
                )
                if preference is None:
                    raise InvalidCommunicationError

            preference.change(enabled=enabled, now=now)
            repositories.streak_reminder_preferences.update(preference)
            return preference.enabled
