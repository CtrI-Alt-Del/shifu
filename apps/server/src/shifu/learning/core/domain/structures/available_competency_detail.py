from decimal import Decimal
from typing import Literal

from shifu.learning.core.domain.enums import (
    CompetencyAvailability,
    CompetencyProgressStatus,
)
from shifu.learning.core.domain.structures.activity_recommendation import (
    ActivityRecommendation,
)
from shifu.learning.core.domain.structures.adaptive_recommendation_detail import (
    AdaptiveRecommendationDetail,
)
from shifu.learning.core.domain.structures.competency_activity_detail import (
    CompetencyActivityDetail,
)
from shifu.learning.core.domain.structures.competency_material_detail import (
    CompetencyMaterialDetail,
)
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import require_percentage


@structure
class AvailableCompetencyDetail:
    goal_id: str
    skill_id: str
    skill_name: str
    competency_id: str
    competency_name: str
    availability: Literal[CompetencyAvailability.AVAILABLE]
    progress: Decimal | None
    status: CompetencyProgressStatus
    is_focus: bool
    focus_returned: bool
    focus_competency_id: str | None
    focus_competency_name: str | None
    items: tuple[CompetencyMaterialDetail | CompetencyActivityDetail, ...]
    recommendation: ActivityRecommendation | None
    adaptive: AdaptiveRecommendationDetail | None = None
    coverage_complete: bool = False
    verification_cause: str | None = None

    def __post_init__(self) -> None:
        if self.progress is not None:
            require_percentage(self.progress)
        if self.focus_returned and not self.is_focus:
            raise ValueError('Only the current focus can be returned.')
        if self.recommendation is not None:
            if not self.is_focus:
                raise ValueError('Only the current focus can be recommended.')
            if self.recommendation.competency_id != self.competency_id:
                raise ValueError('Recommendation must belong to the detail.')
