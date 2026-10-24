from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_FALLBACK_TIME_ZONE = 'UTC'


def resolved_time_zone(time_zone: str | None) -> str:
    """The account's IANA zone, or UTC when it is absent or unresolvable.

    Shared by the practice calendar and the overview so both reads resolve a
    learner's local date identically.
    """
    if not time_zone:
        return _FALLBACK_TIME_ZONE
    try:
        ZoneInfo(time_zone)
    except (ZoneInfoNotFoundError, ValueError):
        return _FALLBACK_TIME_ZONE
    return time_zone
