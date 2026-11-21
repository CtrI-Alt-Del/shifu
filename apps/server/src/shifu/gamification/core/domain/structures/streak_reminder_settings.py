from shifu.gamification.core.domain.enums.streak_reminder_invite_status import (
    StreakReminderInviteStatus,
)
from shifu.shared.core.domain.structures import structure


@structure
class StreakReminderSettings:
    hour: int
    invite_status: StreakReminderInviteStatus
