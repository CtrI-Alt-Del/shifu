from datetime import datetime
from typing import Literal

from shifu.gamification.core.domain.enums import AchievementFamily
from shifu.shared.core.domain.structures import structure

AchievementOverviewState = Literal['obtained', 'locked', 'historical']


@structure
class AchievementOverviewEntry:
    """Read-model row for the Achievements tab; not a persisted entity."""

    code: str
    family: AchievementFamily
    name: str
    description: str
    criterion_label: str
    xp_reward: int
    state: AchievementOverviewState
    unlocked_at: datetime | None
    progress_current: int | None
    progress_target: int | None
