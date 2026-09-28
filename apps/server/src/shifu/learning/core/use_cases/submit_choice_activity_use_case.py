from datetime import UTC

from shifu.learning.core.domain.entities import (
    ActivityAttempt,
    ActivityEvaluation,
    SkillExperience,
)
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityEvaluationStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.structures import (
    ActivityAnswer,
    ChoiceAnswerSubmission,
    ChoiceAttemptDetail,
    MultipleSelectionAnswer,
    SingleChoiceAnswer,
    ChoiceSubmissionOutcome,
    CodeAnswer,
)
from shifu.learning.core.domain.events.activity_submission_requested_event import (
    ActivitySubmissionRequestedEvent,
    ActivitySubmissionRequestedPayload,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases.choice_evidence_eligibility import (
    ChoiceEvidenceEligibility,
)
from shifu.shared.core.domain.errors import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from shifu.shared.core.domain.structures import (
    CurriculumChoiceActivitySnapshot,
    CurriculumLearningActivitySnapshot,
    CurriculumJavascriptStdinQuestionSnapshot,
)
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

    def execute(  # noqa: C901
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
        activity_id: str,
        submission_key: str,
        answers: tuple[ChoiceAnswerSubmission | CodeAnswer, ...],
        activity_revision: str | None = None,
        diagnostic_run_id: str | None = None,
    ) -> ChoiceSubmissionOutcome:
        if not submission_key.strip():
            raise ValidationError
        with self._learning_database.transaction() as repositories:
            goal = repositories.goals.find_by_id(goal_id)
            experience = repositories.skill_experiences.find_by_goal_id_and_skill_id(
                goal_id, skill_id
            )
            if goal is None or goal.account_id != account_id or experience is None:
                raise NotFoundError
            if experience.status is SkillExperienceStatus.DIAGNOSING:
                raise ConflictError
            experience_id = experience.id
            existing = repositories.activity_attempts.find_by_skill_experience_id_and_submission_key(
                experience_id, submission_key
            )
            if existing is not None:
                if existing.kind is ActivityAttemptKind.DIAGNOSTIC:
                    raise ConflictError
                return self._replayed_outcome(
                    repositories, existing, competency_id, activity_id, answers
                )

        mixed_getter = getattr(
            self._curriculum_content_provider, 'get_learning_activity', None
        )
        snapshot = mixed_getter(activity_id) if mixed_getter is not None else None
        if not isinstance(snapshot, CurriculumLearningActivitySnapshot) or not any(
            isinstance(item, CurriculumJavascriptStdinQuestionSnapshot)
            for item in snapshot.questions
        ):
            snapshot = self._curriculum_content_provider.get_choice_activity(
                activity_id
            )
        if (
            snapshot is None
            or snapshot.id != activity_id
            or snapshot.competency_id != competency_id
        ):
            raise NotFoundError
        if snapshot.activity_type == 'diagnostic':
            raise ConflictError
        if (
            isinstance(snapshot, CurriculumLearningActivitySnapshot)
            and snapshot.revision != activity_revision
        ):
            raise ConflictError
        normalized_answers = self.normalize_answers(snapshot, answers)
        v2_catalog = self._curriculum_content_provider.get_skill_content(skill_id)

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
            ):
                raise NotFoundError
            if experience.status is SkillExperienceStatus.DIAGNOSING:
                raise ConflictError

            existing = repositories.activity_attempts.find_by_skill_experience_id_and_submission_key(
                experience_id, submission_key
            )
            if existing is not None:
                if existing.kind is ActivityAttemptKind.DIAGNOSTIC and (
                    diagnostic_run_id is None
                    or existing.diagnostic_run_id != diagnostic_run_id
                    or experience.diagnostic_run_id != diagnostic_run_id
                ):
                    raise ConflictError
                return self._replayed_outcome(
                    repositories, existing, competency_id, activity_id, answers
                )
            if isinstance(
                snapshot, CurriculumChoiceActivitySnapshot
            ) and not ChoiceEvidenceEligibility.is_valid(snapshot, v2_catalog):
                raise NotFoundError

            if snapshot.activity_type != 'learning' or not progress.content_released:
                raise NotFoundError
            if experience.status not in {
                SkillExperienceStatus.LEARNING,
                SkillExperienceStatus.COMPLETED,
            }:
                raise NotFoundError
            kind = (
                ActivityAttemptKind.REVIEW
                if experience.status is SkillExperienceStatus.COMPLETED
                else ActivityAttemptKind.LEARNING
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
                kind=kind,
                answers=normalized_answers,
                submitted_at=now,
                submission_key=submission_key,
                grading_snapshot=snapshot,
                diagnostic_run_id=None,
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
                        kind=kind,
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
                is_diagnostic=False,
            )

    @staticmethod
    def _replayed_outcome(
        repositories: LearningDatabaseRepositories,
        existing: ActivityAttempt,
        competency_id: str,
        activity_id: str,
        answers: tuple[ChoiceAnswerSubmission | CodeAnswer, ...],
    ) -> ChoiceSubmissionOutcome:
        snapshot = existing.grading_snapshot
        if (
            snapshot is None
            or existing.activity_id != activity_id
            or existing.competency_id != competency_id
            or existing.answers
            != SubmitChoiceActivityUseCase.normalize_answers(snapshot, answers)
        ):
            raise ConflictError
        evaluation = repositories.activity_evaluations.find_by_attempt_id(existing.id)
        if evaluation is None:
            raise ConflictError
        return ChoiceSubmissionOutcome(
            attempt=ChoiceAttemptDetail(
                attempt_id=existing.id,
                activity_id=existing.activity_id,
                status=evaluation.status,
                submitted_at=existing.submitted_at,
                retry_allowed=evaluation.status is ActivityEvaluationStatus.FAILED,
            ),
            replayed=True,
            is_diagnostic=existing.kind is ActivityAttemptKind.DIAGNOSTIC,
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
    def normalize_answers(  # noqa: C901
        snapshot: CurriculumChoiceActivitySnapshot | CurriculumLearningActivitySnapshot,
        answers: tuple[ChoiceAnswerSubmission | CodeAnswer, ...],
    ) -> tuple[ActivityAnswer, ...]:
        if len(answers) != len(snapshot.questions):
            raise ValidationError
        normalized: list[ActivityAnswer] = []
        for question, answer in zip(snapshot.questions, answers, strict=True):
            if answer.question_key != question.key:
                raise ValidationError
            if isinstance(question, CurriculumJavascriptStdinQuestionSnapshot):
                if not isinstance(answer, CodeAnswer):
                    raise ValidationError
                editable_paths = {
                    item.path for item in question.initial_files if item.editable
                }
                if (
                    answer.source_code is not None
                    or len({item.path for item in answer.files}) != len(answer.files)
                    or {item.path for item in answer.files} != editable_paths
                ):
                    raise ValidationError
                normalized.append(
                    CodeAnswer(
                        question_key=answer.question_key,
                        files=tuple(sorted(answer.files, key=lambda item: item.path)),
                    )
                )
                continue
            if not isinstance(answer, ChoiceAnswerSubmission):
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
