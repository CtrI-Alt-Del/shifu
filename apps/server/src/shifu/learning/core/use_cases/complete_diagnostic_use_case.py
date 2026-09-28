from datetime import UTC, datetime
from decimal import Decimal

from shifu.learning.core.domain.adaptive_learning_policy import AdaptiveLearningPolicy
from shifu.learning.core.domain.entities import (
    ActivityAttempt,
    ActivityEvaluation,
    Goal,
    SkillExperience,
)
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityDifficulty,
    ActivityEvaluationStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.events.diagnostic_completed_event import (
    DiagnosticCompletedEvent,
    DiagnosticCompletedPayload,
)
from shifu.learning.core.domain.events.skill_completed_event import (
    SkillCompletedEvent,
    SkillCompletedPayload,
)
from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.learning.core.domain.structures import (
    AdaptiveCompetencyMemory,
    CompetencyCompletionSummary,
    ConceptCompletionSummary,
    SkillCompletionSummary,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases.adaptive_policy_context import AdaptivePolicyContext
from shifu.learning.core.use_cases.diagnostic_sequence import DiagnosticSequence
from shifu.shared.core.domain.errors import ConflictError, NotFoundError
from shifu.shared.core.interfaces import ClockProvider, CurriculumContentProvider
from shifu.shared.core.domain.structures import CurriculumSkillSnapshot


class CompleteDiagnosticUseCase:
    def __init__(
        self,
        database: LearningDatabase,
        curriculum: CurriculumContentProvider,
        clock: ClockProvider,
    ) -> None:
        self._database = database
        self._curriculum = curriculum
        self._clock = clock

    def execute(  # noqa: C901
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        diagnostic_run_id: str,
    ) -> SkillExperience:
        with self._database.transaction() as repositories:
            goal = repositories.goals.find_by_id(goal_id)
            experience = repositories.skill_experiences.find_by_goal_id_and_skill_id(
                goal_id, skill_id
            )
            if goal is None or goal.account_id != account_id or experience is None:
                raise NotFoundError
            experience = repositories.skill_experiences.find_by_id_for_update(
                experience.id
            )
            if experience is None:
                raise NotFoundError
            if experience.diagnostic_run_id != diagnostic_run_id:
                raise ConflictError
            if experience.status in {
                SkillExperienceStatus.LEARNING,
                SkillExperienceStatus.COMPLETED,
            }:
                return experience
            if experience.status is not SkillExperienceStatus.DIAGNOSING:
                raise ConflictError

            catalog = self._curriculum.get_skill_content(skill_id)
            if catalog is None or catalog.id != skill_id or not catalog.v2_eligible:
                raise NotFoundError
            attempts = tuple(
                repositories.activity_attempts.find_many_by_skill_experience_id_and_diagnostic_run_id(
                    experience.id, diagnostic_run_id
                )
            )
            evaluations = tuple(
                repositories.activity_evaluations.find_many_by_attempt_ids(
                    tuple(item.id for item in attempts)
                )
            )
            evaluations_by_attempt = {item.attempt_id: item for item in evaluations}
            ordered = DiagnosticSequence.ordered(catalog)
            attempt_by_activity: dict[str, ActivityAttempt] = {}
            for attempt in attempts:
                if (
                    attempt.kind is not ActivityAttemptKind.DIAGNOSTIC
                    or attempt.diagnostic_run_id != diagnostic_run_id
                    or attempt.activity_id in attempt_by_activity
                ):
                    raise ConflictError
                attempt_by_activity[attempt.activity_id] = attempt
            if set(attempt_by_activity) != {activity.id for _, activity in ordered}:
                raise ConflictError
            current_evaluations: list[ActivityEvaluation] = []
            for competency_id, activity in ordered:
                attempt = attempt_by_activity[activity.id]
                if attempt.competency_id != competency_id:
                    raise ConflictError
                evaluation = evaluations_by_attempt.get(attempt.id)
                if (
                    evaluation is None
                    or evaluation.status is not ActivityEvaluationStatus.COMPLETED
                    or evaluation.score is None
                ):
                    raise ConflictError
                current_evaluations.append(evaluation)

            now = self._clock.now()
            self._apply_confirmation(
                repositories,
                goal,
                experience,
                catalog,
                current_evaluations,
                now,
            )
            return experience

    @staticmethod
    def _apply_confirmation(
        repositories: LearningDatabaseRepositories,
        goal: Goal,
        experience: SkillExperience,
        catalog: CurriculumSkillSnapshot,
        evaluations: list[ActivityEvaluation],
        now: datetime,
    ) -> None:
        context = AdaptivePolicyContext.from_skill(catalog)
        observations = tuple(
            repositories.concept_observations.find_many_by_skill_experience_id(
                experience.id
            )
        )
        policy = AdaptiveLearningPolicy().evaluate(
            concepts=context.concepts,
            competency_ids=context.competency_ids,
            activities=context.activities,
            materials=context.materials,
            observations=observations,
            memories=tuple(
                AdaptiveCompetencyMemory(
                    competency_id=item.competency_id,
                    mastered_at=item.mastered_at,
                    content_released=item.content_released,
                )
                for item in repositories.competency_progresses.find_many_by_skill_experience_id(
                    experience.id
                )
            ),
            previous_target_id=experience.recommended_concept_id,
            now=now,
        )
        progress_rows = (
            repositories.competency_progresses.find_many_by_skill_experience_id(
                experience.id
            )
        )
        progress_by_id = {item.competency_id: item for item in progress_rows}
        states_by_id = {item.competency_id: item for item in policy.competency_states}
        concept_states_by_id = {item.concept_id: item for item in policy.concept_states}
        if set(progress_by_id) != set(context.competency_ids):
            raise InvalidAttemptError
        concept_to_competency = {
            item.id: item.competency_id for item in context.concepts
        }
        repositories.concept_states.upsert_many(
            experience.id, concept_to_competency, policy.concept_states, now
        )
        competency_summaries: list[CompetencyCompletionSummary] = []
        for competency_id in context.competency_ids:
            progress = progress_by_id[competency_id]
            state = states_by_id[competency_id]
            concept_states = tuple(
                concept_states_by_id[item.id]
                for item in context.concepts
                if item.competency_id == competency_id
            )
            baselines = tuple(
                item.initial_progress
                for item in concept_states
                if item.initial_progress is not None
            )
            progress.initial_progress = (
                sum(baselines, Decimal('0')) / Decimal(len(baselines))
                if baselines
                else None
            )
            progress.current_progress = state.partial_progress
            progress.status = state.status
            progress.mastered_at = state.mastered_at
            progress.content_released = state.content_released
            progress.coverage_complete = state.coverage_complete
            progress.verification_cause = state.verification_cause
            progress.verification_concept_id = state.verification_concept_id
            progress.updated_at = now
            repositories.competency_progresses.update(progress)
            concept_summaries = tuple(
                ConceptCompletionSummary(
                    concept_id=item.concept_id,
                    initial_progress=item.initial_progress,
                    final_progress=item.progress or Decimal('0'),
                    initial_observed_difficulties=tuple(
                        difficulty
                        for difficulty in ActivityDifficulty
                        if difficulty in item.observed_difficulties
                    ),
                    final_observed_difficulties=tuple(
                        difficulty
                        for difficulty in ActivityDifficulty
                        if difficulty in item.observed_difficulties
                    ),
                )
                for item in concept_states
            )
            competency_summaries.append(
                CompetencyCompletionSummary(
                    competency_id=competency_id,
                    initial_progress=progress.initial_progress,
                    final_progress=state.partial_progress or Decimal('0'),
                    initial_coverage_complete=all(
                        item.coverage_complete for item in concept_states
                    ),
                    concepts=concept_summaries,
                )
            )

        for evaluation in evaluations:
            evaluation.apply_effect(now)
            repositories.activity_evaluations.update(evaluation)
        experience.recommended_concept_id = (
            policy.recommendation.target_concept_id
            if policy.recommendation is not None
            else None
        )
        initial_values = tuple(
            item.initial_progress
            for item in competency_summaries
            if item.initial_progress is not None
        )
        initial = (
            sum(initial_values, Decimal('0')) / Decimal(len(initial_values))
            if initial_values
            else None
        )
        coverage_complete = bool(competency_summaries) and all(
            item.initial_coverage_complete for item in competency_summaries
        )
        if policy.focus_competency_id is None:
            final_values = tuple(item.final_progress for item in competency_summaries)
            final = sum(final_values, Decimal('0')) / Decimal(len(final_values))
            experience.complete(
                SkillCompletionSummary(
                    competencies=tuple(competency_summaries),
                    initial_progress=initial if coverage_complete else None,
                    final_progress=final,
                    started_at=experience.started_at or now,
                    completed_at=now,
                    initial_coverage_complete=coverage_complete,
                ),
                now,
            )
            repositories.events.add(
                SkillCompletedEvent(
                    payload=SkillCompletedPayload(
                        account_id=goal.account_id,
                        goal_id=goal.id,
                        skill_experience_id=experience.id,
                        skill_id=experience.skill_id,
                        initial_progress=(
                            str(initial) if initial is not None else 'unknown'
                        ),
                        final_progress=str(final),
                        completed_at=now.astimezone(UTC)
                        .isoformat()
                        .replace('+00:00', 'Z'),
                    )
                )
            )
        else:
            experience.start_learning(now)
        experience.recommended_concept_id = (
            policy.recommendation.target_concept_id
            if policy.recommendation is not None
            else None
        )
        repositories.skill_experiences.update(experience)
        repositories.events.add(
            DiagnosticCompletedEvent(
                payload=DiagnosticCompletedPayload(
                    account_id=goal.account_id,
                    goal_id=goal.id,
                    skill_experience_id=experience.id,
                    skill_id=experience.skill_id,
                    initial_progress=str(initial) if initial is not None else 'unknown',
                    completed_at=now.astimezone(UTC).isoformat().replace('+00:00', 'Z'),
                )
            )
        )
