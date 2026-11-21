from shifu.communication.core.domain.entities import StreakReminder
from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.communication.core.domain.structures import StreakReminderRequest
from shifu.communication.core.interfaces import CommunicationDatabase
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class QueueStreakReminderUseCase:
    """Record the single daily reminder for an account, ignoring replays."""

    def __init__(
        self,
        database: CommunicationDatabase,
        id_provider: IdentifierProvider,
        clock_provider: ClockProvider,
    ) -> None:
        self._database = database
        self._id_provider = id_provider
        self._clock_provider = clock_provider

    def execute(self, request: StreakReminderRequest) -> StreakReminder:
        with self._database.transaction() as repositories:
            now = self._clock_provider.now()
            reminder = StreakReminder.create(
                id=self._id_provider.generate(),
                account_id=request.account_id,
                local_date=request.local_date,
                streak_days=request.streak_days,
                expires_at=request.expires_at,
                now=now,
            )
            if not repositories.streak_reminders.try_add(reminder):
                existing = (
                    repositories.streak_reminders.find_by_account_id_and_local_date(
                        request.account_id,
                        request.local_date,
                    )
                )
                if existing is None:
                    raise InvalidCommunicationError
                return existing

            preference = repositories.streak_reminder_preferences.find_by_account_id(
                request.account_id
            )
            subscriptions = repositories.push_subscriptions.find_many_by_account_id(
                request.account_id
            )
            if preference is None or not preference.enabled or not subscriptions:
                reminder.skip(now)
                repositories.streak_reminders.update(reminder)
            return reminder
