from shifu.gamification.core.domain.structures.achievement_overview_entry import (
    AchievementOverviewEntry,
)
from shifu.shared.core.domain.structures import structure


@structure
class AchievementsOverview:
    """Read-model bundle for the Achievements tab; not a persisted entity."""

    level: int
    total_xp: int
    xp_for_next_level: int
    achievements: tuple[AchievementOverviewEntry, ...]
