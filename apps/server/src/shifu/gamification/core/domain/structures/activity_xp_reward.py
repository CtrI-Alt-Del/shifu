from shifu.gamification.core.domain.enums import ActivityXpRewardState
from shifu.shared.core.domain.structures import structure


@structure
class ActivityXpReward:
    activity_id: str
    attempt_id: str
    state: ActivityXpRewardState
    additional_xp: int
    granted_xp: int
    maximum_xp: int | None
