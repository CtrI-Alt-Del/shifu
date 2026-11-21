from datetime import datetime

from shifu.gamification.core.domain.errors import GamificationProfileNotFoundError
from shifu.gamification.core.domain.streak_reminder_settings_of import (
    streak_reminder_settings_of,
)
from shifu.gamification.core.domain.structures import StreakReminderSettings
from shifu.gamification.core.interfaces import GamificationDatabase


class AnswerStreakReminderInviteUseCase:
    """Record, once per account, that the learner answered the reminder invite."""

    def __init__(self, database: GamificationDatabase) -> None:
        self._database = database

    def execute(self, account_id: str, *, now: datetime) -> StreakReminderSettings:
        with self._database.transaction() as repositories:
            profile = repositories.profiles.find_by_account_id_for_update(account_id)
            if profile is None:
                raise GamificationProfileNotFoundError
            if profile.reminder_invite_answered_at is None:
                profile.answer_reminder_invite(answered_at=now)
                repositories.profiles.update(profile)
            return streak_reminder_settings_of(profile)
