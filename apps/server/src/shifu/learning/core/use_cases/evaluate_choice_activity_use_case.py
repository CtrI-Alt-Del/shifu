from datetime import UTC, datetime
from decimal import Decimal

from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityDifficulty,
    ActivityEvaluationStatus,
    CompetencyProgressStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.adaptive_learning_policy import AdaptiveLearningPolicy
from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.learning.core.domain.events.activity_evaluated_event import (
    ActivityEvaluatedEvent,
    ActivityEvaluatedPayload,
)
from shifu.learning.core.domain.events.competency_mastered_event import (
    CompetencyMasteredEvent,
    CompetencyMasteredPayload,
)
from shifu.learning.core.domain.events.competency_mastery_lost_event import (
    CompetencyMasteryLostEvent,
    CompetencyMasteryLostPayload,
)
from shifu.learning.core.domain.entities import (
    ActivityAttempt,
    ActivityEvaluation,
    CompetencyProgress,
    Goal,
    SkillExperience,
)
from shifu.learning.core.domain.events.diagnostic_completed_event import (
    DiagnosticCompletedEvent,
    DiagnosticCompletedPayload,
)
from shifu.learning.core.domain.events.skill_completed_event import (
    SkillCompletedEvent,
    SkillCompletedPayload,
)
from shifu.learning.core.domain.structures import (
    AdaptiveCompetencyMemory,
    ActivityAnswer,
    ChoiceEvaluationResult,
    ConceptObservation,
    CompetencyCompletionSummary,
    EvaluationPartResult,
    MultipleSelectionAnswer,
    OfficialActivityResult,
    SingleChoiceAnswer,
    SkillCompletionSummary,
)
from shifu.learning.core.use_cases.adaptive_policy_context import AdaptivePolicyContext
from shifu.learning.core.use_cases.diagnostic_sequence import DiagnosticSequence
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.shared.core.domain.structures import (
    CurriculumChoiceActivitySnapshot,
    CurriculumSkillSnapshot,
)
from shifu.shared.core.interfaces import ClockProvider, CurriculumContentProvider


class EvaluateChoiceActivityUseCase:
    def __init__(
        self,
        learning_database: LearningDatabase,
        clock_provider: ClockProvider,
        curriculum_content_provider: CurriculumContentProvider | None = None,
    ) -> None:
        self._learning_database = learning_database
        self._clock_provider = clock_provider
        self._curriculum_content_provider = curriculum_content_provider

    def execute(self, attempt_id: str, run_id: str) -> None:  # noqa: C901
        now = self._clock_provider.now()
        with self._learning_database.transaction() as repositories:
            attempt = repositories.activity_attempts.find_by_id(attempt_id)
            if attempt is None or attempt.grading_snapshot is None:
                return
            evaluation = (
                repositories.activity_evaluations.find_by_attempt_id_for_update(
                    attempt_id
                )
            )
            if (
                evaluation is None
                or evaluation.status is not ActivityEvaluationStatus.PENDING
                or evaluation.run_id != run_id
            ):
                return
            experience = repositories.skill_experiences.find_by_id_for_update(
                attempt.skill_experience_id
            )
            if experience is None:
                return
            goal = repositories.goals.find_by_id(experience.goal_id)
            if goal is None:
                return
            progress = repositories.competency_progresses.find_by_skill_experience_id_and_competency_id(
                experience.id, attempt.competency_id
            )
            if progress is None:
                raise InvalidAttemptError

            part_results = self._score(attempt.answers, attempt.grading_snapshot)
            score = sum(
                (
                    result.score * part.weight_percentage / Decimal('100')
                    for part, result in zip(
                        attempt.grading_snapshot.parts, part_results, strict=True
                    )
                ),
                start=Decimal('0'),
            )
            status_before = progress.status or CompetencyProgressStatus.LEARNING
            progress_before = progress.current_progress
            if progress_before is None:
                progress_before = progress.initial_progress or Decimal('0')
            evaluation.complete(score, now, part_results)

            if experience.policy_id == AdaptiveLearningPolicy.policy_id:
                self._apply_v2(
                    repositories,
                    goal,
                    experience,
                    attempt,
                    evaluation,
                    part_results,
                    now,
                )
                return

            attempts = repositories.activity_attempts.find_many_by_skill_experience_id(
                experience.id
            )
            competency_attempts = tuple(
                item
                for item in attempts
                if item.competency_id == attempt.competency_id
                and item.grading_snapshot is not None
            )
            evaluations = repositories.activity_evaluations.find_many_by_attempt_ids(
                tuple(item.id for item in competency_attempts)
            )
            evaluations_by_attempt_id = {item.attempt_id: item for item in evaluations}
            evaluations_by_attempt_id[attempt.id] = evaluation
            latest_results: dict[str, OfficialActivityResult] = {}
            hard_activity_ids: set[str] = set()
            for prior_attempt in competency_attempts:
                snapshot = prior_attempt.grading_snapshot
                if snapshot is not None and snapshot.difficulty == 'hard':
                    hard_activity_ids.add(prior_attempt.activity_id)
                prior_evaluation = evaluations_by_attempt_id.get(prior_attempt.id)
                if (
                    prior_evaluation is None
                    or prior_evaluation.status is not ActivityEvaluationStatus.COMPLETED
                    or prior_evaluation.score is None
                    or prior_evaluation.completed_at is None
                ):
                    continue
                latest_results[prior_attempt.activity_id] = OfficialActivityResult(
                    activity_id=prior_attempt.activity_id,
                    attempt_id=prior_attempt.id,
                    score=prior_evaluation.score,
                    submitted_at=prior_attempt.submitted_at,
                    completed_at=prior_evaluation.completed_at,
                )

            status_before_recompute = status_before
            progress.recompute(
                results=tuple(latest_results.values()),
                hard_activity_ids=frozenset(hard_activity_ids),
                updated_at=now,
            )
            progress_after = progress.current_progress or Decimal('0')
            status_after = progress.status or CompetencyProgressStatus.LEARNING
            evaluation.save_progress_effect(
                progress_before=progress_before,
                progress_after=progress_after,
                status_before=status_before_recompute,
                status_after=status_after,
            )
            evaluation.apply_effect(now)
            repositories.competency_progresses.update(progress)
            repositories.activity_evaluations.update(evaluation)

            evaluated_at = now.astimezone(UTC).isoformat().replace('+00:00', 'Z')
            repositories.events.add(
                ActivityEvaluatedEvent(
                    payload=ActivityEvaluatedPayload(
                        account_id=goal.account_id,
                        goal_id=goal.id,
                        skill_experience_id=experience.id,
                        skill_id=experience.skill_id,
                        competency_id=attempt.competency_id,
                        activity_id=attempt.activity_id,
                        attempt_id=attempt.id,
                        evaluation_id=evaluation.id,
                        kind=attempt.kind,
                        difficulty=ActivityDifficulty(
                            attempt.grading_snapshot.difficulty
                        ),
                        score=str(score),
                        evaluated_at=evaluated_at,
                    )
                )
            )
            self._publish_mastery_transition(
                repositories,
                goal,
                experience,
                attempt.competency_id,
                progress_after,
                status_before_recompute,
                status_after,
                progress.mastered_at,
                evaluated_at,
            )

    def _apply_v2(  # noqa: C901
        self,
        repositories: LearningDatabaseRepositories,
        goal: Goal,
        experience: SkillExperience,
        attempt: ActivityAttempt,
        evaluation: ActivityEvaluation,
        part_results: tuple[EvaluationPartResult, ...],
        now: datetime,
    ) -> None:
        provider = self._curriculum_content_provider
        if provider is None:
            raise InvalidAttemptError
        catalog = provider.get_skill_content(experience.skill_id)
        if catalog is None or catalog.id != experience.skill_id:
            raise InvalidAttemptError
        snapshot = attempt.grading_snapshot
        if snapshot is None:
            raise InvalidAttemptError
        if attempt.kind is ActivityAttemptKind.DIAGNOSTIC:
            if (
                experience.status is not SkillExperienceStatus.DIAGNOSING
                or snapshot.activity_type != 'diagnostic'
            ):
                raise InvalidAttemptError
        elif attempt.kind is ActivityAttemptKind.LEARNING:
            if (
                experience.status is not SkillExperienceStatus.LEARNING
                or snapshot.activity_type != 'learning'
            ):
                raise InvalidAttemptError
        elif attempt.kind is ActivityAttemptKind.REVIEW:
            if experience.status is not SkillExperienceStatus.COMPLETED:
                raise InvalidAttemptError
            evaluation.apply_effect(now)
            repositories.activity_evaluations.update(evaluation)
            return
        else:
            raise InvalidAttemptError

        attempts = tuple(
            repositories.activity_attempts.find_many_by_skill_experience_id(
                experience.id
            )
        )
        first_submitted_at = min(
            (
                item.submitted_at
                for item in attempts
                if item.activity_id == attempt.activity_id
            ),
            default=attempt.submitted_at,
        )
        observation_scores: dict[str, list[Decimal | None]] = {}
        result_by_question = {
            item.question_key: item
            for item in part_results
            if isinstance(item, ChoiceEvaluationResult)
        }
        for question in snapshot.questions:
            result = result_by_question.get(question.key)
            if result is None:
                raise InvalidAttemptError
            for criterion in question.concept_criteria:
                observation_scores.setdefault(criterion.concept_id, []).append(
                    criterion.correct_score
                    if result.is_correct
                    else criterion.incorrect_score
                )
        if not observation_scores:
            raise InvalidAttemptError
        catalog_concept_ids = {
            concept.id
            for competency in catalog.competencies
            for concept in competency.concepts
        }
        if not observation_scores.keys() <= catalog_concept_ids:
            raise InvalidAttemptError
        observations = tuple(
            ConceptObservation(
                attempt_id=attempt.id,
                activity_id=attempt.activity_id,
                concept_id=concept_id,
                difficulty=ActivityDifficulty(snapshot.difficulty),
                first_submitted_at=first_submitted_at,
                submitted_at=attempt.submitted_at,
                completed_at=now,
                question_scores=tuple(scores),
                diagnostic=attempt.kind is ActivityAttemptKind.DIAGNOSTIC,
            )
            for concept_id, scores in sorted(observation_scores.items())
        )
        existing = repositories.concept_observations.find_many_by_attempt_id(attempt.id)
        if existing:
            raise InvalidAttemptError
        repositories.concept_observations.add_many(
            experience.id, attempt.competency_id, observations
        )

        if attempt.kind is ActivityAttemptKind.DIAGNOSTIC:
            evaluations = tuple(
                repositories.activity_evaluations.find_many_by_attempt_ids(
                    tuple(item.id for item in attempts)
                )
            )
            current_evaluations = tuple(
                evaluation if item.attempt_id == attempt.id else item
                for item in evaluations
            )
            if all(item.attempt_id != attempt.id for item in current_evaluations):
                current_evaluations += (evaluation,)
            if (
                DiagnosticSequence.next_item(catalog, attempts, current_evaluations)
                is not None
            ):
                evaluation.apply_effect(now)
                repositories.activity_evaluations.update(evaluation)
                return

        all_observations = (
            tuple(
                repositories.concept_observations.find_many_by_skill_experience_id(
                    experience.id
                )
            )
            + observations
        )
        context = AdaptivePolicyContext.from_skill(catalog)
        progress_rows = (
            repositories.competency_progresses.find_many_by_skill_experience_id(
                experience.id
            )
        )
        progress_by_id = {item.competency_id: item for item in progress_rows}
        if set(progress_by_id) != set(context.competency_ids):
            raise InvalidAttemptError
        memories = tuple(
            AdaptiveCompetencyMemory(
                competency_id=item.competency_id,
                mastered_at=item.mastered_at,
                content_released=item.content_released,
            )
            for item in progress_rows
        )
        result = AdaptiveLearningPolicy().evaluate(
            concepts=context.concepts,
            competency_ids=context.competency_ids,
            activities=context.activities,
            materials=context.materials,
            observations=all_observations,
            memories=memories,
            previous_target_id=experience.recommended_concept_id,
            now=now,
        )
        experience.recommended_concept_id = (
            result.recommendation.target_concept_id
            if result.recommendation is not None
            else None
        )
        repositories.skill_experiences.update(experience)
        concept_to_competency = {
            item.id: item.competency_id for item in context.concepts
        }
        repositories.concept_states.upsert_many(
            experience.id, concept_to_competency, result.concept_states, now
        )
        states_by_id = {item.competency_id: item for item in result.competency_states}
        concept_states_by_id = {item.concept_id: item for item in result.concept_states}
        before = progress_by_id[attempt.competency_id]
        status_before = before.status or CompetencyProgressStatus.LEARNING
        progress_before = before.current_progress
        for competency_id in context.competency_ids:
            progress = progress_by_id[competency_id]
            state = states_by_id[competency_id]
            concept_baselines = tuple(
                baseline
                for concept in context.concepts
                if concept.competency_id == competency_id
                if (baseline := concept_states_by_id[concept.id].initial_progress)
                is not None
            )
            progress.initial_progress = (
                sum(concept_baselines, Decimal('0')) / Decimal(len(concept_baselines))
                if concept_baselines
                else None
            )
            progress.current_progress = state.progress
            progress.status = state.status
            progress.mastered_at = state.mastered_at
            progress.content_released = state.content_released
            progress.coverage_complete = state.coverage_complete
            progress.verification_cause = state.verification_cause
            progress.verification_concept_id = state.verification_concept_id
            progress.updated_at = now
            repositories.competency_progresses.update(progress)
        after = progress_by_id[attempt.competency_id]
        if attempt.kind is ActivityAttemptKind.LEARNING:
            evaluation.save_progress_effect(
                progress_before=progress_before,
                progress_after=after.current_progress,
                status_before=status_before,
                status_after=after.status or CompetencyProgressStatus.LEARNING,
            )
        evaluation.apply_effect(now)
        repositories.activity_evaluations.update(evaluation)
        evaluated_at = now.astimezone(UTC).isoformat().replace('+00:00', 'Z')
        if attempt.kind is ActivityAttemptKind.DIAGNOSTIC:
            repositories.events.add(
                DiagnosticCompletedEvent(
                    payload=DiagnosticCompletedPayload(
                        account_id=goal.account_id,
                        goal_id=goal.id,
                        skill_experience_id=experience.id,
                        skill_id=experience.skill_id,
                        initial_progress=self._aggregate_progress(progress_rows),
                        completed_at=evaluated_at,
                    )
                )
            )
            if result.focus_competency_id is None:
                self._complete_skill(
                    repositories, goal, experience, catalog, progress_rows, now
                )
            else:
                experience.start_learning(now)
                repositories.skill_experiences.update(experience)
            return

        repositories.events.add(
            ActivityEvaluatedEvent(
                payload=ActivityEvaluatedPayload(
                    account_id=goal.account_id,
                    goal_id=goal.id,
                    skill_experience_id=experience.id,
                    skill_id=experience.skill_id,
                    competency_id=attempt.competency_id,
                    activity_id=attempt.activity_id,
                    attempt_id=attempt.id,
                    evaluation_id=evaluation.id,
                    kind=attempt.kind,
                    difficulty=ActivityDifficulty(snapshot.difficulty),
                    score=str(evaluation.score),
                    evaluated_at=evaluated_at,
                )
            )
        )
        self._publish_mastery_transition(
            repositories,
            goal,
            experience,
            attempt.competency_id,
            after.current_progress or Decimal('0'),
            status_before,
            after.status or CompetencyProgressStatus.LEARNING,
            after.mastered_at,
            evaluated_at,
        )
        if result.focus_competency_id is None:
            self._complete_skill(
                repositories, goal, experience, catalog, progress_rows, now
            )

    @staticmethod
    def _aggregate_progress(progress_rows: list[CompetencyProgress]) -> str:
        values = tuple(
            item.initial_progress
            for item in progress_rows
            if item.initial_progress is not None
        )
        if not values:
            return 'unknown'
        return str(sum(values, Decimal('0')) / Decimal(len(values)))

    @staticmethod
    def _complete_skill(
        repositories: LearningDatabaseRepositories,
        goal: Goal,
        experience: SkillExperience,
        catalog: CurriculumSkillSnapshot,
        progress_rows: list[CompetencyProgress],
        now: datetime,
    ) -> None:
        by_id = {item.competency_id: item for item in progress_rows}
        summaries = tuple(
            CompetencyCompletionSummary(
                competency_id=competency.id,
                initial_progress=by_id[competency.id].initial_progress,
                final_progress=by_id[competency.id].current_progress or Decimal('0'),
            )
            for competency in catalog.competencies
        )
        known_initial = tuple(
            item.initial_progress
            for item in summaries
            if item.initial_progress is not None
        )
        initial = (
            sum(known_initial, Decimal('0')) / Decimal(len(known_initial))
            if known_initial
            else None
        )
        final = sum(
            (item.final_progress for item in summaries), Decimal('0')
        ) / Decimal(len(summaries))
        summary = SkillCompletionSummary(
            competencies=summaries,
            initial_progress=initial,
            final_progress=final,
            started_at=experience.started_at or now,
            completed_at=now,
        )
        experience.complete(summary, now)
        repositories.skill_experiences.update(experience)
        repositories.events.add(
            SkillCompletedEvent(
                payload=SkillCompletedPayload(
                    account_id=goal.account_id,
                    goal_id=goal.id,
                    skill_experience_id=experience.id,
                    skill_id=experience.skill_id,
                    initial_progress=str(initial) if initial is not None else 'unknown',
                    final_progress=str(final),
                    completed_at=now.astimezone(UTC).isoformat().replace('+00:00', 'Z'),
                )
            )
        )

    @staticmethod
    def _publish_mastery_transition(
        repositories: LearningDatabaseRepositories,
        goal: Goal,
        experience: SkillExperience,
        competency_id: str,
        progress: Decimal,
        status_before: CompetencyProgressStatus,
        status_after: CompetencyProgressStatus,
        mastered_at: datetime | None,
        evaluated_at: str,
    ) -> None:
        if (
            status_before is not CompetencyProgressStatus.MASTERED
            and status_after is CompetencyProgressStatus.MASTERED
            and mastered_at is not None
        ):
            repositories.events.add(
                CompetencyMasteredEvent(
                    payload=CompetencyMasteredPayload(
                        account_id=goal.account_id,
                        goal_id=goal.id,
                        skill_experience_id=experience.id,
                        skill_id=experience.skill_id,
                        competency_id=competency_id,
                        progress=str(progress),
                        mastered_at=mastered_at.astimezone(UTC)
                        .isoformat()
                        .replace('+00:00', 'Z'),
                    )
                )
            )
        elif (
            status_before is CompetencyProgressStatus.MASTERED
            and status_after is not CompetencyProgressStatus.MASTERED
        ):
            repositories.events.add(
                CompetencyMasteryLostEvent(
                    payload=CompetencyMasteryLostPayload(
                        account_id=goal.account_id,
                        goal_id=goal.id,
                        skill_experience_id=experience.id,
                        skill_id=experience.skill_id,
                        competency_id=competency_id,
                        progress=str(progress),
                        lost_at=evaluated_at,
                    )
                )
            )

    @staticmethod
    def _score(
        answers: tuple[ActivityAnswer, ...],
        snapshot: CurriculumChoiceActivitySnapshot,
    ) -> tuple[EvaluationPartResult, ...]:
        answers_by_key = {answer.question_key: answer for answer in answers}
        questions_by_key = {question.key: question for question in snapshot.questions}
        if len(answers_by_key) != len(answers) or set(answers_by_key) != set(
            questions_by_key
        ):
            raise InvalidAttemptError
        results: list[EvaluationPartResult] = []
        for part in snapshot.parts:
            question = questions_by_key.get(part.question_key)
            answer = answers_by_key.get(part.question_key)
            if question is None or answer is None:
                raise InvalidAttemptError
            if question.kind == 'single_choice':
                if not isinstance(answer, SingleChoiceAnswer):
                    raise InvalidAttemptError
                selected = {answer.selected_option_key}
            else:
                if not isinstance(answer, MultipleSelectionAnswer):
                    raise InvalidAttemptError
                selected = set(answer.selected_option_keys)
            correct = {option.key for option in question.options if option.is_correct}
            is_correct = selected == correct
            results.append(
                ChoiceEvaluationResult(
                    question_key=question.key,
                    score=Decimal('100') if is_correct else Decimal('0'),
                    is_correct=is_correct,
                    explanation=(
                        question.correct_explanation
                        if is_correct
                        else question.incorrect_explanation
                    ),
                )
            )
        return tuple(results)
