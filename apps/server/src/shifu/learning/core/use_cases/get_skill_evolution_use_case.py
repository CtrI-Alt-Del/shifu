from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from shifu.learning.core.domain.entities import ActivityEvaluation
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityDifficulty,
    ActivityEvaluationStatus,
)
from shifu.learning.core.domain.errors import SkillExperienceNotFoundError
from shifu.learning.core.domain.structures import (
    ConceptObservation,
    SkillEvolution,
    SkillEvolutionPoint,
)
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.demonstrated_progress import demonstrated_progress
from shifu.shared.core.interfaces import CurriculumContentProvider

_PERSISTED_PRECISION = Decimal('0.01')


class GetSkillEvolutionUseCase:
    def __init__(
        self,
        database: LearningDatabase,
        curriculum_content_provider: CurriculumContentProvider,
    ) -> None:
        self._database = database
        self._curriculum_content_provider = curriculum_content_provider

    def execute(self, account_id: str, skill_experience_id: str) -> SkillEvolution:
        """Raises SkillExperienceNotFoundError when the experience does not
        exist or its Goal belongs to another account."""
        with self._database.transaction() as repositories:
            experience = repositories.skill_experiences.find_by_id(skill_experience_id)
            if experience is None:
                raise SkillExperienceNotFoundError

            goal = repositories.goals.find_by_id(experience.goal_id)
            if goal is None or goal.account_id != account_id:
                raise SkillExperienceNotFoundError

            learning_attempt_ids = tuple(
                attempt.id
                for attempt in repositories.activity_attempts.find_many_by_skill_experience_id(
                    experience.id
                )
                if attempt.kind is ActivityAttemptKind.LEARNING
            )
            evaluations = (
                repositories.activity_evaluations.find_many_by_attempt_ids(
                    learning_attempt_ids
                )
                if learning_attempt_ids
                else []
            )
            observations = tuple(
                repositories.concept_observations.find_many_by_skill_experience_id(
                    experience.id
                )
            )

        content = self._curriculum_content_provider.get_skill_content(
            experience.skill_id
        )
        if content is None:
            raise SkillExperienceNotFoundError

        concept_ids = tuple(
            concept.id
            for competency in content.competencies
            for concept in competency.concepts
        )
        points: list[SkillEvolutionPoint] = []
        baseline = _baseline_point(concept_ids, observations)
        if baseline is not None:
            points.append(baseline)

        previous = points[-1].result if points else None
        for completed_at, result in _official_learning_results(evaluations):
            if previous is not None and result == previous:
                continue

            points.append(
                SkillEvolutionPoint(
                    occurred_at=completed_at,
                    result=result,
                    is_partial=_is_partial(concept_ids, observations, completed_at),
                    is_baseline=False,
                )
            )
            previous = result

        return SkillEvolution(
            skill_experience_id=experience.id,
            points=tuple(points),
        )


def _official_learning_results(
    evaluations: list[ActivityEvaluation],
) -> list[tuple[datetime, Decimal]]:
    """Completion instant and Habilidade result of every official evaluation."""
    results = sorted(
        (evaluation.completed_at, evaluation.attempt_id, evaluation.progress_after)
        for evaluation in evaluations
        if evaluation.status is ActivityEvaluationStatus.COMPLETED
        and evaluation.completed_at is not None
        and evaluation.progress_after is not None
    )
    return [(completed_at, result) for completed_at, _, result in results]


def _baseline_point(
    concept_ids: tuple[str, ...],
    observations: tuple[ConceptObservation, ...],
) -> SkillEvolutionPoint | None:
    diagnostic = tuple(item for item in observations if item.diagnostic)
    result = demonstrated_progress(
        tuple(
            _diagnostic_baseline(concept_id, diagnostic) for concept_id in concept_ids
        )
    )
    if result is None:
        return None

    occurred_at = max(item.completed_at for item in diagnostic)
    return SkillEvolutionPoint(
        occurred_at=occurred_at,
        # Evaluation results are persisted with two decimals; the base uses the
        # same precision so an unchanged result is never read as a change.
        result=result.quantize(_PERSISTED_PRECISION, rounding=ROUND_HALF_UP),
        is_partial=_is_partial(concept_ids, observations, occurred_at),
        is_baseline=True,
    )


def _current_valid(
    concept_id: str,
    observations: tuple[ConceptObservation, ...],
) -> tuple[ConceptObservation, ...]:
    """Latest numeric observation per Activity, as the adaptive policy keeps it."""
    latest: dict[str, ConceptObservation] = {}
    for item in sorted(
        observations, key=lambda item: (item.completed_at, item.attempt_id)
    ):
        if item.concept_id == concept_id and item.value is not None:
            latest[item.activity_id] = item
    return tuple(latest.values())


def _diagnostic_baseline(
    concept_id: str,
    diagnostic: tuple[ConceptObservation, ...],
) -> Decimal | None:
    """Mean of the per-difficulty means of the Concept's diagnostic evidence."""
    current = _current_valid(concept_id, diagnostic)
    difficulty_means: list[Decimal] = []
    for difficulty in ActivityDifficulty:
        values = [
            item.value
            for item in current
            if item.difficulty is difficulty and item.value is not None
        ]
        if values:
            difficulty_means.append(sum(values, Decimal('0')) / Decimal(len(values)))

    if not difficulty_means:
        return None

    return sum(difficulty_means, Decimal('0')) / Decimal(len(difficulty_means))


def _is_partial(
    concept_ids: tuple[str, ...],
    observations: tuple[ConceptObservation, ...],
    at: datetime,
) -> bool:
    """A result is partial while some Concept lacks a valid current observation
    in each of the three difficulties, counting only evidence completed by ``at``."""
    known = tuple(item for item in observations if item.completed_at <= at)
    return not concept_ids or any(
        frozenset(item.difficulty for item in _current_valid(concept_id, known))
        != frozenset(ActivityDifficulty)
        for concept_id in concept_ids
    )
