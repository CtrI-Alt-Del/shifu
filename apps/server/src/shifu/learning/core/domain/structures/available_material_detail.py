from typing import Literal

from shifu.learning.core.domain.enums import CompetencyAvailability
from shifu.learning.core.domain.structures.activity_recommendation import (
    ActivityRecommendation,
)
from shifu.shared.core.domain.structures import structure


@structure
class AvailableMaterialDetail:
    goal_id: str
    skill_id: str
    skill_name: str
    competency_id: str
    competency_name: str
    material_id: str
    material_title: str
    availability: Literal[CompetencyAvailability.AVAILABLE]
    content: str
    recommendation: ActivityRecommendation | None

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError('Material content cannot be empty.')
        if (
            self.recommendation is not None
            and self.recommendation.competency_id != self.competency_id
        ):
            raise ValueError('Recommendation must belong to the source Competency.')
