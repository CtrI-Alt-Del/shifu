from datetime import UTC

from shifu.learning.core.domain.entities import (
    ActivityAttempt,
    ActivityEvaluation,
    SkillExperience,
)
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityEvaluationStatus,
)
from shifu.learning.core.domain.structures import (
    ActivityAnswer,
    ChoiceAnswerSubmission,
    ChoiceAttemptDetail,
    MultipleSelectionAnswer,
    SingleChoiceAnswer,
    ChoiceSubmissionOutcome,
)
from shifu.learning.core.domain.events.activity_submission_requested_event import (
    ActivitySubmissionRequestedEvent,
    ActivitySubmissionRequestedPayload,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.shared.core.domain.errors import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from shifu.shared.core.domain.structures import CurriculumChoiceActivitySnapshot
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumContentProvider,
    IdentifierProvider,
)


class SubmitChoiceActivityUseCase:
    def __init__(
        self,
        learning_database: LearningDatabase,
        curriculum_content_provider: CurriculumContentProvider,
        clock_provider: ClockProvider,
        identifier_provider: IdentifierProvider,
    ) -> None:
        self._learning_database = learning_database
        self._curriculum_content_provider = curriculum_content_provider
        self._clock_provider = clock_provider
        self._identifier_provider = identifier_provider

    def execute(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
        activity_id: str,
        submission_key: str,
        answers: tuple[ChoiceAnswerSubmission, ...],
    ) -> ChoiceSubmissionOutcome:
        if not submission_key.strip():
            raise ValidationError
        with self._learning_database.transaction() as repositories:
            experience = self._owned_released_experience(
                repositories, account_id, goal_id, skill_id, competency_id
            )
            experience_id = experience.id

        snapshot = self._curriculum_content_provider.get_choice_activity(activity_id)
        if (
            snapshot is None
            or snapshot.id != activity_id
            or snapshot.competency_id != competency_id
        ):
            raise NotFoundError
        normalized_answers = self._normalize_answers(snapshot, answers)

        now = self._clock_provider.now()
        with self._learning_database.transaction() as repositories:
            goal = repositories.goals.find_by_id(goal_id)
            experience = repositories.skill_experiences.find_by_id_for_update(
                experience_id
            )
            progress = repositories.competency_progresses.find_by_skill_experience_id_and_competency_id(
                experience_id, competency_id
            )
            if (
                goal is None
                or goal.account_id != account_id
                or experience is None
                or experience.goal_id != goal_id
                or experience.skill_id != skill_id
                or progress is None
                or not progress.content_released
            ):
                raise NotFoundError

            existing = repositories.activity_attempts.find_by_skill_experience_id_and_submission_key(
                experience_id, submission_key
            )
            if existing is not None:
                if existing.answers != normalized_answers:
                    raise ConflictError
                evaluation = repositories.activity_evaluations.find_by_attempt_id(
                    existing.id
                )
                if evaluation is None:
                    raise ConflictError
                return ChoiceSubmissionOutcome(
                    attempt=ChoiceAttemptDetail(
                        attempt_id=existing.id,
                        activity_id=existing.activity_id,
                        status=evaluation.status,
                        submitted_at=existing.submitted_at,
                        retry_allowed=evaluation.status
                        is ActivityEvaluationStatus.FAILED,
                    ),
                    replayed=True,
                )

            unresolved = repositories.activity_evaluations.find_unresolved_by_skill_experience_id(
                experience_id
            )
            if unresolved is not None:
                raise ConflictError

            attempt_id = self._identifier_provider.generate()
            evaluation_id = self._identifier_provider.generate()
            run_id = self._identifier_provider.generate()
            attempt = ActivityAttempt.create(
                id=attempt_id,
                skill_experience_id=experience_id,
                competency_id=competency_id,
                activity_id=activity_id,
                kind=ActivityAttemptKind.LEARNING,
                answers=normalized_answers,
                submitted_at=now,
                submission_key=submission_key,
                grading_snapshot=snapshot,
            )
            evaluation = ActivityEvaluation.create(
                id=evaluation_id,
                attempt_id=attempt_id,
                status=ActivityEvaluationStatus.PENDING,
                parts=(),
                started_at=now,
                run_id=run_id,
            )
            repositories.activity_attempts.add(attempt)
            repositories.activity_evaluations.add(evaluation)
            repositories.events.add(
                ActivitySubmissionRequestedEvent(
                    payload=ActivitySubmissionRequestedPayload(
                        attempt_id=attempt_id,
                        run_id=run_id,
                        skill_experience_id=experience_id,
                        activity_id=activity_id,
                        kind=ActivityAttemptKind.LEARNING,
                        requested_at=now.astimezone(UTC)
                        .isoformat()
                        .replace('+00:00', 'Z'),
                    )
                )
            )
            return ChoiceSubmissionOutcome(
                attempt=ChoiceAttemptDetail(
                    attempt_id=attempt_id,
                    activity_id=activity_id,
                    status=ActivityEvaluationStatus.PENDING,
                    submitted_at=now,
                    retry_allowed=False,
                ),
                replayed=False,
            )

    @staticmethod
    def _owned_released_experience(
        repositories: LearningDatabaseRepositories,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
    ) -> SkillExperience:
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
        progress = repositories.competency_progresses.find_by_skill_experience_id_and_competency_id(
            experience.id, competency_id
        )
        if (
            progress is None
            or progress.skill_experience_id != experience.id
            or not progress.content_released
        ):
            raise NotFoundError
        return experience

    @staticmethod
    def _normalize_answers(
        snapshot: CurriculumChoiceActivitySnapshot,
        answers: tuple[ChoiceAnswerSubmission, ...],
    ) -> tuple[ActivityAnswer, ...]:
        if len(answers) != len(snapshot.questions):
            raise ValidationError
        normalized: list[ActivityAnswer] = []
        for question, answer in zip(snapshot.questions, answers, strict=True):
            if answer.question_key != question.key:
                raise ValidationError
            option_keys = {option.key for option in question.options}
            selected = answer.selected_option_keys
            if not selected or len(set(selected)) != len(selected):
                raise ValidationError
            if not set(selected).issubset(option_keys):
                raise ValidationError
            if question.kind == 'single_choice':
                if len(selected) != 1:
                    raise ValidationError
                normalized.append(
                    SingleChoiceAnswer(
                        question_key=answer.question_key,
                        selected_option_key=selected[0],
                    )
                )
            else:
                normalized.append(
                    MultipleSelectionAnswer(
                        question_key=answer.question_key,
                        selected_option_keys=selected,
                    )
                )
        return tuple(normalized)
