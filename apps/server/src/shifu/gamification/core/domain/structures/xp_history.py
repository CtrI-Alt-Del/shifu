from shifu.gamification.core.domain.structures.xp_history_entry import XpHistoryEntry
from shifu.shared.core.domain.structures import structure


@structure
class XpHistory:
    """The account's complete XP ledger, newest concession first.

    `total_xp` is summed from `entries` rather than read from the profile, so
    the presented total is always explainable by exactly the records presented
    beside it.
    """

    total_xp: int
    entries: tuple[XpHistoryEntry, ...]
