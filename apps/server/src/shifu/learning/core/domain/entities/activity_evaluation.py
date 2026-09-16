from datetime import datetime
from decimal import Decimal

from shifu.learning.core.domain.enums import ActivityEvaluationStatus
from shifu.learning.core.domain.structures import EvaluationPartResult
from shifu.shared.core.domain.entities import entity


@entity
class ActivityEvaluation:
    id: str
    attempt_id: str
    status: ActivityEvaluationStatus
    parts: tuple[EvaluationPartResult, ...]
    started_at: datetime
    score: Decimal | None = None
    failure_code: str | None = None
    completed_at: datetime | None = None
    effect_applied_at: datetime | None = None
