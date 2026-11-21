from dataclasses import field
from typing import ClassVar

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class StreakReminderDuePayload:
    account_id: str
    local_date: str
    slot_start: str


@structure
class StreakReminderDueEvent(Event[StreakReminderDuePayload]):
    EVENT_NAME: ClassVar[str] = 'gamification/streak-reminder.due'
    name: str = field(default=EVENT_NAME, init=False)
