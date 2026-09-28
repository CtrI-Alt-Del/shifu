from decimal import Decimal
from typing import Literal

from shifu.learning.core.domain.enums import (
    ActivityEvaluationStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.structures.diagnostic_competency_summary import (
    DiagnosticCompetencySummary,
)
from shifu.learning.core.domain.structures.skill_recommendation import (
    SkillRecommendation,
)
from shifu.shared.core.domain.structures import structure

DiagnosticRunState = Literal['requires_entry', 'active', 'ready_to_complete', 'settled']


@structure
class DiagnosticOverview:
    status: SkillExperienceStatus
    run_state: DiagnosticRunState = 'requires_entry'
    activity_sequence: tuple[tuple[str, str], ...] = ()
    ready_to_complete: bool = False
    next_competency_id: str | None = None
    next_activity_id: str | None = None
    pending_attempt_id: str | None = None
    pending_attempt_status: ActivityEvaluationStatus | None = None
    focus_competency_id: str | None = None
    competencies: tuple[DiagnosticCompetencySummary, ...] = ()
    initial_overall_result: Decimal | None = None
    overall_coverage_complete: bool = False
    direct_completion: bool = False
    initial_recommendation: SkillRecommendation | None = None
    initial_recommendation_gap: str | None = None
