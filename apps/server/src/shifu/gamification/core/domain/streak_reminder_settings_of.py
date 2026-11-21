from shifu.gamification.core.domain.entities import GamificationProfile
from shifu.gamification.core.domain.enums import StreakReminderInviteStatus
from shifu.gamification.core.domain.structures import StreakReminderSettings


def streak_reminder_settings_of(profile: GamificationProfile) -> StreakReminderSettings:
    """The learner-visible reminder hour and invite state of one profile.

    The invite is not eligible until the first recognized practice day, which
    is exactly when the longest streak leaves zero.
    """
    if profile.streak.longest == 0:
        status = StreakReminderInviteStatus.NOT_ELIGIBLE
    elif profile.reminder_invite_answered_at is not None:
        status = StreakReminderInviteStatus.ANSWERED
    else:
        status = StreakReminderInviteStatus.PENDING
    return StreakReminderSettings(hour=profile.reminder_hour, invite_status=status)
