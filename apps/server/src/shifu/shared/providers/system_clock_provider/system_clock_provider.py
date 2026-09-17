"""System-backed UTC clock provider."""

from datetime import UTC, datetime

from shifu.shared.core.interfaces import ClockProvider


class SystemClockProvider(ClockProvider):
    """Return the current timezone-aware UTC datetime from the system clock."""

    def now(self) -> datetime:
        return datetime.now(tz=UTC)
