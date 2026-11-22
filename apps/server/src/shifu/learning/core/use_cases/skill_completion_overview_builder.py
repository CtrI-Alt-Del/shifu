import logging
from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from shifu.learning.core.domain.adaptive_learning_policy import (
    AdaptiveLearningPolicy,
)
from shifu.learning.core.domain.entities import (
    ActivityAttempt,
    ActivityEvaluation,
    CompetencyProgress,
)
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityDifficulty,
    ActivityEvaluationStatus,
    StartingPointCoverage,
)
from shifu.learning.core.domain.structures import (
    CompetencyCompletionOverview,
    CompetencyCompletionSummary,
    ConceptObservation,
    SkillCompletionOverview,
    SkillCompletionSummary,
    SkillReviewOverview,
)
from shifu.shared.core.domain.resolved_time_zone import resolved_time_zone
from shifu.shared.core.domain.structures import CurriculumCompetencySnapshot

_logger = logging.getLogger(__name__)

_ALL_DIFFICULTIES = frozenset(ActivityDifficulty)


def build_skill_completion_overview(
    *,
    skill_experience_id: str,
    summary: SkillCompletionSummary,
    competencies: tuple[CurriculumCompetencySnapshot, ...],
    progress_rows: Iterable[CompetencyProgress],
    observations: tuple[ConceptObservation, ...],
    attempts: Iterable[ActivityAttempt],
    evaluations: Iterable[ActivityEvaluation],
    time_zone: str | None,
) -> SkillCompletionOverview:
    """Assemble the read-only completion overview of a completed experience."""
    zone = ZoneInfo(resolved_time_zone(time_zone))
    started_on = _local_day(summary.started_at, zone)
    completed_on = _local_day(summary.completed_at, zone)
    attempts_by_kind = _attempts_by_kind(attempts)
    learning_attempts = attempts_by_kind[ActivityAttemptKind.LEARNING]
    completed_by_diagnosis = not learning_attempts
    mastered_at_by_competency = {
        progress.competency_id: progress.mastered_at
        for progress in progress_rows
        if progress.skill_experience_id == skill_experience_id
    }
    curriculum_by_id = {competency.id: competency for competency in competencies}

    overviews: list[CompetencyCompletionOverview] = []
    for stored in summary.competencies:
        current = curriculum_by_id.get(stored.competency_id)
        if current is None:
            _logger.warning(
                'skill_completion_competency_missing '
                'skill_experience_id=%s competency_id=%s',
                skill_experience_id,
                stored.competency_id,
            )
            continue

        mastered_at = mastered_at_by_competency.get(stored.competency_id)
        overviews.append(
            CompetencyCompletionOverview(
                competency_id=stored.competency_id,
                competency_name=current.name,
                position=current.position,
                initial_progress=stored.initial_progress,
                initial_coverage=_starting_coverage(stored, current, observations),
                final_progress=stored.final_progress,
                mastered_on=(
                    completed_on
                    if completed_by_diagnosis or mastered_at is None
                    else _local_day(mastered_at, zone)
                ),
            )
        )
    ordered = tuple(sorted(overviews, key=lambda item: item.position))
    initial_result, initial_result_coverage = _overall_start(ordered)

    return SkillCompletionOverview(
        started_on=started_on,
        completed_on=completed_on,
        duration_days=(completed_on - started_on).days,
        completed_by_diagnosis=completed_by_diagnosis,
        learning_activity_count=(
            None
            if completed_by_diagnosis
            else len({attempt.activity_id for attempt in learning_attempts})
        ),
        learning_attempt_count=(
            None if completed_by_diagnosis else len(learning_attempts)
        ),
        initial_result=initial_result,
        initial_result_coverage=initial_result_coverage,
        final_result=summary.final_progress,
        competencies=ordered,
        review=_review(attempts_by_kind[ActivityAttemptKind.REVIEW], evaluations),
    )


def _local_day(instant: datetime, zone: ZoneInfo) -> date:
    return instant.astimezone(zone).date()


def _attempts_by_kind(
    attempts: Iterable[ActivityAttempt],
) -> dict[ActivityAttemptKind, list[ActivityAttempt]]:
    grouped: dict[ActivityAttemptKind, list[ActivityAttempt]] = {
        kind: [] for kind in ActivityAttemptKind
    }
    for attempt in attempts:
        grouped[attempt.kind].append(attempt)
    return grouped


def _starting_coverage(
    stored: CompetencyCompletionSummary,
    current: CurriculumCompetencySnapshot,
    observations: tuple[ConceptObservation, ...],
) -> StartingPointCoverage:
    if stored.initial_progress is None:
        return StartingPointCoverage.UNKNOWN

    if stored.concepts:
        covered = tuple(
            _ALL_DIFFICULTIES.issubset(concept.initial_observed_difficulties)
            for concept in stored.concepts
        )
    else:
        covered = tuple(
            _ALL_DIFFICULTIES.issubset(
                AdaptiveLearningPolicy.diagnostic_observed_difficulties(
                    concept.id, observations
                )
            )
            for concept in current.concepts
        )

    return (
        StartingPointCoverage.COMPLETE
        if covered and all(covered)
        else StartingPointCoverage.PARTIAL
    )


def _overall_start(
    competencies: tuple[CompetencyCompletionOverview, ...],
) -> tuple[Decimal | None, StartingPointCoverage]:
    known = tuple(
        item.initial_progress
        for item in competencies
        if item.initial_progress is not None
    )
    if not known:
        return None, StartingPointCoverage.UNKNOWN

    mean = sum(known, start=Decimal('0')) / Decimal(len(known))
    complete = all(
        item.initial_coverage is StartingPointCoverage.COMPLETE for item in competencies
    )
    return mean, (
        StartingPointCoverage.COMPLETE if complete else StartingPointCoverage.PARTIAL
    )


def _review(
    review_attempts: list[ActivityAttempt],
    evaluations: Iterable[ActivityEvaluation],
) -> SkillReviewOverview:
    review_attempt_ids = {attempt.id for attempt in review_attempts}
    finished: list[tuple[datetime, Decimal]] = []
    for evaluation in evaluations:
        if (
            evaluation.attempt_id not in review_attempt_ids
            or evaluation.status is not ActivityEvaluationStatus.COMPLETED
            or evaluation.completed_at is None
            or evaluation.score is None
        ):
            continue

        finished.append((evaluation.completed_at, evaluation.score))

    latest = max(finished, key=lambda item: item[0], default=None)
    return SkillReviewOverview(
        attempt_count=len(review_attempts),
        latest_score=latest[1] if latest is not None else None,
    )
