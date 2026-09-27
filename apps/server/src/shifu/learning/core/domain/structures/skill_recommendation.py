from shifu.learning.core.domain.enums import (
    ActivityDifficulty,
    ActivityRecommendationType,
)
from shifu.shared.core.domain.structures import structure


@structure
class SkillRecommendation:
    competency_id: str
    competency_name: str
    activity_id: str
    activity_title: str
    difficulty: ActivityDifficulty
    type: ActivityRecommendationType
