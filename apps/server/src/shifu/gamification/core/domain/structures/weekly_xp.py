from datetime import date

from shifu.shared.core.domain.structures import structure


@structure
class WeeklyXp:
    """The XP of every grant whose fact date falls in one local week.

    `week_start` is the local Monday that opens the Monday-to-Sunday week.
    """

    week_start: date
    xp: int
