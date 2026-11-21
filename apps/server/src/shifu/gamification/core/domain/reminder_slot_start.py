from datetime import UTC, datetime

from shifu.gamification.core.domain.errors import InvalidGamificationError

SLOT_MINUTES = 15


def require_reminder_slot_start(slot_start: datetime) -> datetime:
    """The slot start as an aligned UTC instant, or an invalid-input error.

    A reminder slot is a window of `SLOT_MINUTES` that starts at `:00`, `:15`,
    `:30` or `:45` UTC. Anything naive or unaligned could not belong to the
    schedule and would silently match no learner.
    """
    if (
        type(slot_start) is not datetime
        or slot_start.tzinfo is None
        or slot_start.utcoffset() is None
    ):
        raise InvalidGamificationError
    instant = slot_start.astimezone(UTC)
    if (
        instant.minute % SLOT_MINUTES != 0
        or instant.second != 0
        or instant.microsecond != 0
    ):
        raise InvalidGamificationError
    return instant
