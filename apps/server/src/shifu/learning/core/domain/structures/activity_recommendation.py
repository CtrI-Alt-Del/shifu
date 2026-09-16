from shifu.learning.core.domain.enums import (
    ActivityDifficulty,
    ActivityRecommendationType,
)
from shifu.shared.core.domain.structures import structure


@structure
class ActivityRecommendation:
    competency_id: str
    activity_id: str
    difficulty: ActivityDifficulty
    type: ActivityRecommendationType
