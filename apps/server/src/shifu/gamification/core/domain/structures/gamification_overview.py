from shifu.gamification.core.domain.structures.achievements_summary import (
    AchievementsSummary,
)
from shifu.gamification.core.domain.structures.streak_overview import StreakOverview
from shifu.shared.core.domain.structures import structure


@structure
class GamificationOverview:
    """Read-model bundle for the Visão geral tab; not a persisted entity.

    `xp_for_next_level` is always at least 1 and `level_percentage` never
    reaches 100: the profile invariant keeps `total_xp` below the next
    level's minimum, so a learner who crosses a threshold has already been
    ratcheted to the level above.
    """

    level: int
    total_xp: int
    current_level_xp: int
    next_level_xp: int
    xp_for_next_level: int
    level_percentage: int
    streak: StreakOverview
    achievements: AchievementsSummary
