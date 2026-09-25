from shifu.learning.core.domain.enums import ActivityDifficulty
from shifu.shared.core.domain.structures import structure


@structure
class AdaptiveRecommendationDetail:
    target_concept_id: str
    target_concept_name: str
    original_target_concept_id: str
    original_target_concept_name: str
    recommended_competency_id: str | None
    material_competency_id: str | None
    reason: str
    difficulty: ActivityDifficulty | None
    activity_id: str | None
    material_id: str | None
    material_is_optional: bool
    gap: str | None
