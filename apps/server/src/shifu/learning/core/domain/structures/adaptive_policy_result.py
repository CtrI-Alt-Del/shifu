from shifu.learning.core.domain.structures.adaptive_competency_state import (
    AdaptiveCompetencyState,
)
from shifu.learning.core.domain.structures.adaptive_concept_state import (
    AdaptiveConceptState,
)
from shifu.learning.core.domain.structures.adaptive_recommendation import (
    AdaptiveRecommendation,
)
from shifu.shared.core.domain.structures import structure


@structure
class AdaptivePolicyResult:
    concept_states: tuple[AdaptiveConceptState, ...]
    competency_states: tuple[AdaptiveCompetencyState, ...]
    focus_competency_id: str | None
    recommendation: AdaptiveRecommendation | None
