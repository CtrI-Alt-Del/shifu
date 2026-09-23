from datetime import UTC, datetime
from decimal import Decimal

from shifu.learning.core.domain.enums import (
    ActivityDifficulty,
    ActivityEvaluationStatus,
    CompetencyProgressStatus,
)
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
from shifu.learning.core.domain.entities import Goal, SkillExperience
from shifu.learning.core.domain.structures import (
    ActivityAnswer,
    ChoiceEvaluationResult,
    EvaluationPartResult,
    MultipleSelectionAnswer,
    OfficialActivityResult,
    SingleChoiceAnswer,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.shared.core.domain.structures import CurriculumChoiceActivitySnapshot
from shifu.shared.core.interfaces import ClockProvider


class EvaluateChoiceActivityUseCase:
    def __init__(
        self,
        learning_database: LearningDatabase,
        clock_provider: ClockProvider,
    ) -> None:
        self._learning_database = learning_database
        self._clock_provider = clock_provider

    def execute(self, attempt_id: str, run_id: str) -> None:
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
