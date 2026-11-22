from shifu.gamification.core.domain.enums.achievement_criterion_kind import (
    AchievementCriterionKind,
)
from shifu.shared.core.domain.structures import structure


@structure
class NextAchievement:
    """The locked active achievement closest to its criterion; not persisted.

    `progress_current` is already clamped to `progress_target`, so a value
    reached but not yet recognized never reads above its target.
    """

    achievement_id: str
    name: str
    criterion_label: str
    criterion_kind: AchievementCriterionKind
    xp_reward: int
    progress_current: int
    progress_target: int
