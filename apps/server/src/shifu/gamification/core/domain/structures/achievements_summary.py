from shifu.gamification.core.domain.structures.recent_achievement import (
    RecentAchievement,
)
from shifu.shared.core.domain.structures import structure


@structure
class AchievementsSummary:
    """The overview's achievements block; not a persisted entity.

    `obtained_count` counts only holdings still present in the active
    catalog, so it always reads as a coherent ratio against `catalog_count`.
    """

    recent: tuple[RecentAchievement, ...]
    obtained_count: int
    catalog_count: int
