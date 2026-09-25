from datetime import datetime
from decimal import Decimal

from shifu.learning.core.domain.enums import (
    ActivityEvaluationStatus,
    CompetencyProgressStatus,
)
from shifu.learning.core.domain.structures.activity_recommendation import (
    ActivityRecommendation,
)
from shifu.learning.core.domain.structures.choice_result_detail import (
    ChoiceResultDetail,
)
from shifu.shared.core.domain.structures import structure


@structure
class ChoiceAttemptDetail:
    attempt_id: str
    activity_id: str
    status: ActivityEvaluationStatus
    submitted_at: datetime
    retry_allowed: bool
    score: Decimal | None = None
    failure_message: str | None = None
    progress_before: Decimal | None = None
    progress_after: Decimal | None = None
    status_before: CompetencyProgressStatus | None = None
    status_after: CompetencyProgressStatus | None = None
    next_action: ActivityRecommendation | None = None
    questions: tuple[ChoiceResultDetail, ...] = ()
