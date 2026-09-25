from shifu.learning.core.domain.enums import ActivityDifficulty
from shifu.shared.core.domain.structures import structure


@structure
class AdaptiveRecommendation:
    competency_id: str
    target_concept_id: str
    original_target_concept_id: str
    reason: str
    difficulty: ActivityDifficulty | None
    activity_id: str | None
    material_id: str | None = None
    gap: str | None = None
    recommended_competency_id: str | None = None
    material_competency_id: str | None = None

    @property
    def material_is_optional(self) -> bool:
        return self.material_id is not None
