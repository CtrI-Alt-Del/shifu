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
from shifu.learning.core.domain.adaptive_learning_policy import AdaptiveLearningPolicy
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
from shifu.learning.core.use_cases.diagnostic_sequence import DiagnosticSequence
from shifu.learning.core.use_cases.choice_evidence_eligibility import (
    ChoiceEvidenceEligibility,
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

    def execute(  # noqa: C901
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
            goal = repositories.goals.find_by_id(goal_id)
            experience = repositories.skill_experiences.find_by_goal_id_and_skill_id(
                goal_id, skill_id
            )
            if goal is None or goal.account_id != account_id or experience is None:
                raise NotFoundError
            experience_id = experience.id
            existing = repositories.activity_attempts.find_by_skill_experience_id_and_submission_key(
                experience_id, submission_key
            )
            if existing is not None:
                return self._replayed_outcome(
                    repositories, existing, competency_id, activity_id, answers
                )

        snapshot = self._curriculum_content_provider.get_choice_activity(activity_id)
        if (
            snapshot is None
            or snapshot.id != activity_id
            or snapshot.competency_id != competency_id
        ):
            raise NotFoundError
        normalized_answers = self._normalize_answers(snapshot, answers)
        v2_catalog = (
            self._curriculum_content_provider.get_skill_content(skill_id)
            if experience.policy_id == AdaptiveLearningPolicy.policy_id
            else None
        )

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

            existing = repositories.activity_attempts.find_by_skill_experience_id_and_submission_key(
                experience_id, submission_key
            )
            if existing is not None:
                return self._replayed_outcome(
                    repositories, existing, competency_id, activity_id, answers
                )
            if (
                experience.policy_id == AdaptiveLearningPolicy.policy_id
                and not ChoiceEvidenceEligibility.is_valid(snapshot, v2_catalog)
            ):
                raise NotFoundError

            diagnostic = (
                experience.policy_id == AdaptiveLearningPolicy.policy_id
                and experience.status is SkillExperienceStatus.DIAGNOSING
            )
            if diagnostic:
                if (
                    snapshot.activity_type != 'diagnostic'
                    or v2_catalog is None
                    or not v2_catalog.v2_eligible
                ):
                    raise NotFoundError
                kind = ActivityAttemptKind.DIAGNOSTIC
            elif experience.policy_id == AdaptiveLearningPolicy.policy_id:
                if (
                    snapshot.activity_type != 'learning'
                    or not progress.content_released
                ):
                    raise NotFoundError
                kind = (
                    ActivityAttemptKind.REVIEW
                    if experience.status is SkillExperienceStatus.COMPLETED
                    else ActivityAttemptKind.LEARNING
                )
                if experience.status not in {
                    SkillExperienceStatus.LEARNING,
                    SkillExperienceStatus.COMPLETED,
                }:
                    raise NotFoundError
            else:
                if not progress.content_released:
                    raise NotFoundError
                kind = ActivityAttemptKind.LEARNING

            if diagnostic:
                if v2_catalog is None:
                    raise NotFoundError
                diagnostic_attempts = tuple(
                    repositories.activity_attempts.find_many_by_skill_experience_id(
                        experience_id
                    )
                )
                diagnostic_evaluations = tuple(
                    repositories.activity_evaluations.find_many_by_attempt_ids(
                        tuple(item.id for item in diagnostic_attempts)
                    )
                )
                next_item = DiagnosticSequence.next_item(
                    v2_catalog, diagnostic_attempts, diagnostic_evaluations
                )
                if (
                    next_item is None
                    or next_item[0] != competency_id
                    or next_item[1].id != activity_id
                    or next_item[2] is not None
                ):
                    raise ConflictError
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
                is_diagnostic=kind is ActivityAttemptKind.DIAGNOSTIC,
            )

    @staticmethod
    def _replayed_outcome(
        repositories: LearningDatabaseRepositories,
        existing: ActivityAttempt,
        competency_id: str,
        activity_id: str,
        answers: tuple[ChoiceAnswerSubmission, ...],
    ) -> ChoiceSubmissionOutcome:
        snapshot = existing.grading_snapshot
        if (
            snapshot is None
            or existing.activity_id != activity_id
            or existing.competency_id != competency_id
            or existing.answers
            != SubmitChoiceActivityUseCase._normalize_answers(snapshot, answers)
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
