from decimal import Decimal

from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.domain.structures.skill_competency_summary import (
    SkillCompetencySummary,
)
from shifu.learning.core.domain.structures.skill_evaluation_state import (
    SkillEvaluationState,
)
from shifu.learning.core.domain.structures.skill_recommendation import (
    SkillRecommendation,
)
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import require_percentage


@structure
class SkillExperienceDetail:
    goal_id: str
    skill_id: str
    skill_name: str
    skill_status: SkillExperienceStatus
    overall_result: Decimal
    focus_competency_id: str | None
    focus_competency_name: str | None
    competencies: tuple[SkillCompetencySummary, ...]
    recommendation: SkillRecommendation | None
    evaluation: SkillEvaluationState | None

    def __post_init__(self) -> None:
        require_percentage(self.overall_result)
        positions = [competency.position for competency in self.competencies]
        if positions != sorted(positions):
            raise ValueError('Competencies follow the curricular order.')
        focused = [
            competency for competency in self.competencies if competency.is_focus
        ]
        if len(focused) > 1:
            raise ValueError('Only one Competency can be in focus.')
        if focused and focused[0].competency_id != self.focus_competency_id:
            raise ValueError('The focused Competency must be the declared focus.')
        if self.recommendation is not None:
            if self.focus_competency_id is None:
                raise ValueError('A recommendation requires a focus.')
            if self.recommendation.competency_id != self.focus_competency_id:
                raise ValueError('The recommendation belongs to the focus.')
            if self.evaluation is not None:
                raise ValueError('A held evaluation suspends the recommendation.')
