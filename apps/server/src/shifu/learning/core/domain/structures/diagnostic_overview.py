from shifu.learning.core.domain.enums import (
    ActivityEvaluationStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.structures.diagnostic_competency_summary import (
    DiagnosticCompetencySummary,
)
from shifu.shared.core.domain.structures import structure


@structure
class DiagnosticOverview:
    status: SkillExperienceStatus
    next_competency_id: str | None
    next_activity_id: str | None
    pending_attempt_id: str | None
    pending_attempt_status: ActivityEvaluationStatus | None = None
    focus_competency_id: str | None = None
    competencies: tuple[DiagnosticCompetencySummary, ...] = ()
