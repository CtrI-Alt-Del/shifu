from datetime import datetime

from shifu.shared.core.domain.structures import structure


@structure
class RecentAchievement:
    """One obtained achievement as the overview summary presents it.

    Every field is the account's own snapshot rather than the current
    catalog, so a retired achievement keeps the text it was obtained under.
    """

    achievement_id: str
    name: str
    criterion_label: str
    xp_reward: int
    achieved_at: datetime
