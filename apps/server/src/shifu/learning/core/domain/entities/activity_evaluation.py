from datetime import datetime
from decimal import Decimal

from shifu.learning.core.domain.enums import ActivityEvaluationStatus
from shifu.learning.core.domain.errors import (
    EvaluationAlreadyCompletedError,
    EvaluationPendingError,
    EvaluationUnavailableError,
)
from shifu.learning.core.domain.structures import EvaluationPartResult
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.validation import require_percentage


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

    def __post_init__(self) -> None:
        if self.score is not None:
            require_percentage(self.score, EvaluationUnavailableError)
        if self.status is ActivityEvaluationStatus.COMPLETED and (
            self.score is None or self.completed_at is None
        ):
            raise EvaluationUnavailableError
        if self.status is ActivityEvaluationStatus.FAILED and not self.failure_code:
            raise EvaluationUnavailableError

    @classmethod
    def create(
        cls,
        *,
        id: str,
        attempt_id: str,
        status: ActivityEvaluationStatus,
        parts: tuple[EvaluationPartResult, ...],
        started_at: datetime,
        score: Decimal | None = None,
        failure_code: str | None = None,
        completed_at: datetime | None = None,
        effect_applied_at: datetime | None = None,
    ) -> 'ActivityEvaluation':
        return cls(
            id=id,
            attempt_id=attempt_id,
            status=status,
            parts=parts,
            started_at=started_at,
            score=score,
            failure_code=failure_code,
            completed_at=completed_at,
            effect_applied_at=effect_applied_at,
        )

    def complete(
        self,
        score: Decimal,
        completed_at: datetime,
        parts: tuple[EvaluationPartResult, ...],
    ) -> None:
        if self.status is ActivityEvaluationStatus.COMPLETED:
            raise EvaluationAlreadyCompletedError
        if self.status is ActivityEvaluationStatus.FAILED:
            raise EvaluationUnavailableError
        require_percentage(score, EvaluationUnavailableError)
        self.status = ActivityEvaluationStatus.COMPLETED
        self.score = score
        self.parts = parts
        self.completed_at = completed_at
        self.failure_code = None

    def fail(self, failure_code: str) -> None:
        if self.status is ActivityEvaluationStatus.COMPLETED:
            raise EvaluationAlreadyCompletedError
        if self.status is ActivityEvaluationStatus.FAILED:
            raise EvaluationUnavailableError
        self.status = ActivityEvaluationStatus.FAILED
        self.failure_code = failure_code

    def retry(self, started_at: datetime) -> None:
        if self.status is not ActivityEvaluationStatus.FAILED:
            raise EvaluationPendingError
        self.status = ActivityEvaluationStatus.PENDING
        self.started_at = started_at
        self.failure_code = None

    def apply_effect(self, applied_at: datetime) -> None:
        if self.status is not ActivityEvaluationStatus.COMPLETED:
            raise EvaluationPendingError
        if self.effect_applied_at is not None:
            raise EvaluationAlreadyCompletedError
        self.effect_applied_at = applied_at
