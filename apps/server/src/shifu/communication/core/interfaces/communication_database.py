from contextlib import AbstractContextManager
from typing import Protocol

from shifu.communication.core.interfaces.communications_repository import (
    CommunicationsRepository,
)
from shifu.communication.core.interfaces.delivery_attempts_repository import (
    DeliveryAttemptsRepository,
)
from shifu.communication.core.interfaces.push_deliveries_repository import (
    PushDeliveriesRepository,
)
from shifu.communication.core.interfaces.push_subscriptions_repository import (
    PushSubscriptionsRepository,
)
from shifu.communication.core.interfaces.streak_reminder_preferences_repository import (
    StreakReminderPreferencesRepository,
)
from shifu.communication.core.interfaces.streak_reminders_repository import (
    StreakRemindersRepository,
)
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.interfaces import EventsRepository


@structure
class CommunicationDatabaseRepositories:
    communications: CommunicationsRepository
    delivery_attempts: DeliveryAttemptsRepository
    push_subscriptions: PushSubscriptionsRepository
    streak_reminder_preferences: StreakReminderPreferencesRepository
    streak_reminders: StreakRemindersRepository
    push_deliveries: PushDeliveriesRepository
    events: EventsRepository


class CommunicationDatabase(Protocol):
    def transaction(
        self,
    ) -> AbstractContextManager[CommunicationDatabaseRepositories]:
        """Open the transaction boundary for one Communication operation."""
        ...
