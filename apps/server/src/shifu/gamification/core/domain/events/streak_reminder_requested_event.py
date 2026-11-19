from dataclasses import field
from typing import ClassVar

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class StreakReminderRequestedPayload:
    account_id: str
    local_date: str
    streak_days: int
    expires_at: str


@structure
class StreakReminderRequestedEvent(Event[StreakReminderRequestedPayload]):
    EVENT_NAME: ClassVar[str] = 'gamification/streak-reminder.requested'
    name: str = field(default=EVENT_NAME, init=False)
