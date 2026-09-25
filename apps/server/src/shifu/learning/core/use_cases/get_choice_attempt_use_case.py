from datetime import timedelta
from decimal import Decimal

from shifu.learning.core.domain.entities import ActivityAttempt, ActivityEvaluation
from shifu.learning.core.domain.adaptive_learning_policy import AdaptiveLearningPolicy
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityDifficulty,
    ActivityEvaluationStatus,
    ActivityRecommendationType,
    CompetencyProgressStatus,
)
from shifu.learning.core.domain.structures import (
    ActivityRecommendation,
    ChoiceEvaluationResult,
    ChoiceAttemptDetail,
    ChoiceResultDetail,
    MultipleSelectionAnswer,
    SingleChoiceAnswer,
)
from shifu.learning.core.interfaces import LearningDatabase
from shifu.shared.core.domain.errors import NotFoundError
from shifu.shared.core.domain.structures import (
    CurriculumActivitySnapshot,
    CurriculumSkillSnapshot,
)
from shifu.shared.core.interfaces import ClockProvider, CurriculumContentProvider


class GetChoiceAttemptUseCase:
    _TIMEOUT = timedelta(minutes=5)

    def __init__(
        self,
        learning_database: LearningDatabase,
        curriculum_content_provider: CurriculumContentProvider,
        clock_provider: ClockProvider,
    ) -> None:
        self._learning_database = learning_database
        self._curriculum_content_provider = curriculum_content_provider
        self._clock_provider = clock_provider

    def execute(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
        activity_id: str,
        attempt_id: str,
    ) -> ChoiceAttemptDetail:
        now = self._clock_provider.now()
        with self._learning_database.transaction() as repositories:
            goal = repositories.goals.find_by_id(goal_id)
            if goal is None or goal.id != goal_id or goal.account_id != account_id:
                raise NotFoundError
            experience = repositories.skill_experiences.find_by_goal_id_and_skill_id(
                goal_id, skill_id
            )
            if (
                experience is None
                or experience.goal_id != goal_id
                or experience.skill_id != skill_id
            ):
                raise NotFoundError
            attempt = repositories.activity_attempts.find_by_id(attempt_id)
            if (
                attempt is None
                or attempt.skill_experience_id != experience.id
                or attempt.competency_id != competency_id
                or attempt.activity_id != activity_id
                or attempt.kind is ActivityAttemptKind.DIAGNOSTIC
                or attempt.grading_snapshot is None
            ):
                raise NotFoundError
            evaluation = (
                repositories.activity_evaluations.find_by_attempt_id_for_update(
                    attempt.id
                )
            )
            if evaluation is None:
                raise NotFoundError
            if (
                evaluation.status is ActivityEvaluationStatus.PENDING
                and now >= evaluation.started_at + self._TIMEOUT
            ):
                evaluation.time_out('evaluation_timeout')
                repositories.activity_evaluations.update(evaluation)

            if evaluation.status is not ActivityEvaluationStatus.COMPLETED:
                return ChoiceAttemptDetail(
                    attempt_id=attempt.id,
                    activity_id=attempt.activity_id,
                    status=evaluation.status,
                    submitted_at=attempt.submitted_at,
                    retry_allowed=evaluation.status is ActivityEvaluationStatus.FAILED,
                    failure_message=(
                        'A avaliação falhou. Você pode tentar novamente.'
                        if evaluation.status is ActivityEvaluationStatus.FAILED
                        else None
                    ),
                )

            all_attempts = (
                repositories.activity_attempts.find_many_by_skill_experience_id(
                    experience.id
                )
            )
            all_evaluations = (
                repositories.activity_evaluations.find_many_by_attempt_ids(
                    tuple(item.id for item in all_attempts)
                )
            )
            progress = repositories.competency_progresses.find_by_skill_experience_id_and_competency_id(
                experience.id, competency_id
            )
            is_mastered = (
                progress is not None
                and progress.status is CompetencyProgressStatus.MASTERED
            )
            disclosure = self._released_question_keys(
                attempt,
                all_attempts,
                all_evaluations,
                is_mastered,
                evaluation,
            )
            detail = self._result_detail(attempt, evaluation, disclosure)
            next_action_context = (
                experience.skill_id,
                progress.current_progress
                if progress is not None and progress.current_progress is not None
                else (progress.initial_progress if progress is not None else None),
                tuple(all_attempts),
                tuple(all_evaluations),
            )
            is_adaptive = experience.policy_id == AdaptiveLearningPolicy.policy_id
            score = evaluation.score
            progress_before = evaluation.progress_before
            progress_after = evaluation.progress_after
            status_before = evaluation.status_before
            status_after = evaluation.status_after

        recommendation = None
        if not is_adaptive:
            skill_content = self._curriculum_content_provider.get_skill_content(
                next_action_context[0]
            )
            recommendation = self._recommendation(
                skill_content,
                competency_id,
                next_action_context[1],
                next_action_context[2],
                next_action_context[3],
            )
        return ChoiceAttemptDetail(
            attempt_id=attempt.id,
            activity_id=attempt.activity_id,
            status=evaluation.status,
            submitted_at=attempt.submitted_at,
            retry_allowed=False,
            score=score,
            progress_before=progress_before,
            progress_after=progress_after,
            status_before=status_before,
            status_after=status_after,
            next_action=recommendation,
            questions=detail,
        )

    @staticmethod
    def _released_question_keys(
        current_attempt: ActivityAttempt,
        attempts: list[ActivityAttempt],
        evaluations: list[ActivityEvaluation],
        is_mastered: bool,
        current_evaluation: ActivityEvaluation,
    ) -> frozenset[str]:
        snapshot = current_attempt.grading_snapshot
        if snapshot is None:
            return frozenset()
        if is_mastered:
            return frozenset(question.key for question in snapshot.questions)
        evaluations_by_attempt = {item.attempt_id: item for item in evaluations}
        released: set[str] = {
            item.question_key
            for item in current_evaluation.parts
            if isinstance(item, ChoiceEvaluationResult) and item.is_correct
        }
        for later_attempt in attempts:
            if (
                later_attempt.activity_id != current_attempt.activity_id
                or later_attempt.competency_id != current_attempt.competency_id
                or later_attempt.submitted_at <= current_attempt.submitted_at
            ):
                continue
            later_evaluation = evaluations_by_attempt.get(later_attempt.id)
            if (
                later_evaluation is None
                or later_evaluation.status is not ActivityEvaluationStatus.COMPLETED
            ):
                continue
            released.update(
                item.question_key
                for item in later_evaluation.parts
                if isinstance(item, ChoiceEvaluationResult) and item.is_correct
            )
        return frozenset(released)

    @staticmethod
    def _result_detail(
        attempt: ActivityAttempt,
        evaluation: ActivityEvaluation,
        disclosed_keys: frozenset[str],
    ) -> tuple[ChoiceResultDetail, ...]:
        snapshot = attempt.grading_snapshot
        if snapshot is None:
            raise NotFoundError
        answers = {answer.question_key: answer for answer in attempt.answers}
        results: dict[str, ChoiceEvaluationResult] = {
            result.question_key: result
            for result in evaluation.parts
            if isinstance(result, ChoiceEvaluationResult)
        }
        details: list[ChoiceResultDetail] = []
        for question in snapshot.questions:
            answer = answers.get(question.key)
            result = results.get(question.key)
            if answer is None or result is None:
                continue
            if isinstance(answer, SingleChoiceAnswer):
                selected_keys = (answer.selected_option_key,)
            elif isinstance(answer, MultipleSelectionAnswer):
                selected_keys = answer.selected_option_keys
            else:
                continue
            details.append(
                ChoiceResultDetail(
                    question_key=question.key,
                    prompt=question.prompt,
                    selected_option_keys=selected_keys,
                    score=result.score,
                    is_correct=result.is_correct,
                    explanation=result.explanation,
                    disclosed_correct_option_keys=(
                        tuple(
                            option.key
                            for option in question.options
                            if option.is_correct
                        )
                        if question.key in disclosed_keys
                        else ()
                    ),
                )
            )
        return tuple(details)

    @staticmethod
    def _recommendation(
        skill_content: CurriculumSkillSnapshot | None,
        competency_id: str,
        progress: Decimal | None,
        attempts: tuple[ActivityAttempt, ...],
        evaluations: tuple[ActivityEvaluation, ...],
    ) -> ActivityRecommendation | None:
        if skill_content is None:
            return None
        competency = next(
            (item for item in skill_content.competencies if item.id == competency_id),
            None,
        )
        if competency is None:
            return None
        target_difficulty = (
            ActivityDifficulty.EASY
            if (progress or Decimal('0')) < Decimal('40')
            else ActivityDifficulty.MEDIUM
            if (progress or Decimal('0')) < Decimal('70')
            else ActivityDifficulty.HARD
        )
        activity_items = tuple(
            item
            for item in competency.items
            if isinstance(item, CurriculumActivitySnapshot)
            and item.activity_type == 'learning'
        )
        evaluation_by_attempt = {item.attempt_id: item for item in evaluations}
        latest_attempt_by_activity: dict[str, ActivityAttempt] = {}
        for attempt in attempts:
            if attempt.competency_id != competency_id:
                continue
            latest_attempt_by_activity[attempt.activity_id] = attempt
        scored_activity_ids = {
            attempt_id
            for attempt_id, evaluation in evaluation_by_attempt.items()
            if evaluation.status is ActivityEvaluationStatus.COMPLETED
            and evaluation.score is not None
        }
        candidates = tuple(
            item
            for item in activity_items
            if ActivityDifficulty(item.difficulty) is target_difficulty
        )
        if not candidates:
            return None
        chosen = candidates[0]
        recent_attempt = attempts[-1] if attempts else None
        if len(candidates) > 1 and recent_attempt is not None:
            chosen = next(
                (item for item in candidates if item.id != recent_attempt.activity_id),
                chosen,
            )
        latest_scored = (
            latest_attempt_by_activity.get(chosen.id) is not None
            and latest_attempt_by_activity[chosen.id].id in scored_activity_ids
        )
        return ActivityRecommendation(
            competency_id=competency_id,
            activity_id=chosen.id,
            difficulty=target_difficulty,
            type=(
                ActivityRecommendationType.REINFORCEMENT
                if latest_scored
                else ActivityRecommendationType.NEW_ACTIVITY
            ),
        )
