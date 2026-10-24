from datetime import datetime

from shifu.gamification.core.domain.enums import XpSource
from shifu.shared.core.domain.structures import structure


@structure
class XpHistoryEntry:
    """Read-model row for the XP history; not a persisted entity."""

    grant_id: str
    amount: int
    source: XpSource
    title: str
    detail: str
    occurred_at: datetime
    granted_at: datetime
