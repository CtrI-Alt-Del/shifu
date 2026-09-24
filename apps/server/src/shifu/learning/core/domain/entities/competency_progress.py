from datetime import datetime
from decimal import Decimal

from shifu.learning.core.domain.enums import ActivityDifficulty
from shifu.learning.core.domain.enums import CompetencyProgressStatus
from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.learning.core.domain.structures import OfficialActivityResult
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.validation import require_percentage


@entity
class CompetencyProgress:
    id: str
    skill_experience_id: str
    competency_id: str
    content_released: bool
    created_at: datetime
    updated_at: datetime
    initial_progress: Decimal | None = None
    current_progress: Decimal | None = None
    status: CompetencyProgressStatus | None = None
    mastered_at: datetime | None = None
    hard_activity_score: Decimal | None = None
    coverage_complete: bool = False
    verification_cause: str | None = None
    verification_concept_id: str | None = None

    def __post_init__(self) -> None:
        for progress in (
            self.initial_progress,
            self.current_progress,
            self.hard_activity_score,
        ):
            if progress is not None:
                require_percentage(progress, InvalidAttemptError)
        if (
            self.status is CompetencyProgressStatus.MASTERED
            and self.mastered_at is None
        ):
            raise InvalidAttemptError

    def recompute(
        self,
        *,
        results: tuple[OfficialActivityResult, ...],
        hard_activity_ids: frozenset[str],
        updated_at: datetime,
    ) -> None:
        previous_status = self.status
        latest_by_activity: dict[str, OfficialActivityResult] = {}
        for result in sorted(results, key=lambda item: item.completed_at):
            latest_by_activity[result.activity_id] = result
        ordered_results = tuple(
            sorted(latest_by_activity.values(), key=lambda item: item.completed_at)
        )
        progress = self.initial_progress or Decimal('0')
        for result in ordered_results:
            progress = progress * Decimal('0.7') + result.score * Decimal('0.3')
        self.current_progress = progress
        self.updated_at = updated_at
        self.hard_activity_score = max(
            (
                result.score
                for result in ordered_results
                if result.activity_id in hard_activity_ids
            ),
            default=None,
        )
        self.status = self._status_for_current_progress()
        if self.status is CompetencyProgressStatus.MASTERED:
            self.mastered_at = (
                self.mastered_at
                if previous_status is CompetencyProgressStatus.MASTERED
                else updated_at
            )
        else:
            self.mastered_at = None

    def record_result(
        self,
        *,
        score: Decimal,
        difficulty: ActivityDifficulty,
        updated_at: datetime,
    ) -> None:
        """Preserve the legacy domain API; new evaluation flows use recompute."""
        require_percentage(score, InvalidAttemptError)
        previous = self.current_progress or Decimal('0')
        self.current_progress = previous * Decimal('0.7') + score * Decimal('0.3')
        self.updated_at = updated_at
        if difficulty is ActivityDifficulty.HARD:
            self.hard_activity_score = max(
                self.hard_activity_score or Decimal('0'), score
            )
        self.status = self._status_for_current_progress()
        if self.status is CompetencyProgressStatus.MASTERED:
            self.mastered_at = self.mastered_at or updated_at
        else:
            self.mastered_at = None

    def _status_for_current_progress(self) -> CompetencyProgressStatus:
        progress = self.current_progress or Decimal('0')
        if progress >= Decimal('85') and (
            self.hard_activity_score or Decimal('0')
        ) >= Decimal('80'):
            return CompetencyProgressStatus.MASTERED
        if progress >= Decimal('70'):
            return CompetencyProgressStatus.PROFICIENT
        if progress >= Decimal('40'):
            return CompetencyProgressStatus.DEVELOPING
        return CompetencyProgressStatus.LEARNING
