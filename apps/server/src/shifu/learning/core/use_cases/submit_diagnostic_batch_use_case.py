from dataclasses import dataclass
from datetime import UTC, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid5

from shifu.learning.core.domain.entities import ActivityAttempt, ActivityEvaluation
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityEvaluationStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.events.activity_submission_requested_event import (
    ActivitySubmissionRequestedEvent,
    ActivitySubmissionRequestedPayload,
)
from shifu.learning.core.domain.structures import (
    ActivityAnswer,
    ChoiceAnswerSubmission,
    CodeAnswer,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases.diagnostic_sequence import DiagnosticSequence
from shifu.learning.core.use_cases.get_choice_activity_use_case import (
    GetChoiceActivityUseCase,
)
from shifu.learning.core.use_cases.submit_choice_activity_use_case import (
    SubmitChoiceActivityUseCase,
)
from shifu.shared.core.domain.errors import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumContentProvider,
    IdentifierProvider,
)

if TYPE_CHECKING:
    from shifu.shared.core.domain.structures import CurriculumLearningActivitySnapshot


@dataclass(frozen=True)
class DiagnosticSubmissionItem:
    competency_id: str
    activity_id: str
    activity_revision: str
    answers: tuple[ChoiceAnswerSubmission | CodeAnswer, ...]


@dataclass(frozen=True)
class DiagnosticBatchOutcome:
    replayed: bool


class SubmitDiagnosticBatchUseCase:
    def __init__(
        self,
        database: LearningDatabase,
        curriculum: CurriculumContentProvider,
        clock: ClockProvider,
        identifiers: IdentifierProvider,
    ) -> None:
        self._database = database
        self._curriculum = curriculum
        self._clock = clock
        self._identifiers = identifiers

    def execute(  # noqa: C901 - atomic authorization, replay, validation and writes
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        diagnostic_run_id: str,
        submission_key: UUID,
        items: tuple[DiagnosticSubmissionItem, ...],
    ) -> DiagnosticBatchOutcome:
        if not items:
            raise ValidationError

        with self._database.transaction() as repositories:
            goal = repositories.goals.find_by_id(goal_id)
            experience = repositories.skill_experiences.find_by_goal_id_and_skill_id(
                goal_id, skill_id
            )
            if goal is None or goal.account_id != account_id or experience is None:
                raise NotFoundError

            locked = repositories.skill_experiences.find_by_id_for_update(experience.id)
            if (
                locked is None
                or locked.goal_id != goal_id
                or locked.skill_id != skill_id
                or locked.status is not SkillExperienceStatus.DIAGNOSING
                or locked.diagnostic_run_id != diagnostic_run_id
            ):
                raise ConflictError

            keys = tuple(str(uuid5(submission_key, item.activity_id)) for item in items)
            if len(set(keys)) != len(keys):
                raise ValidationError

            previous = tuple(
                repositories.activity_attempts.find_by_skill_experience_id_and_submission_key(
                    locked.id, key
                )
                for key in keys
            )
            if any(attempt is not None for attempt in previous):
                if any(attempt is None for attempt in previous):
                    raise ConflictError

                self._validate_replay(
                    repositories, locked.id, diagnostic_run_id, items, previous
                )
                return DiagnosticBatchOutcome(replayed=True)

            if repositories.activity_attempts.find_many_by_skill_experience_id_and_diagnostic_run_id(
                locked.id, diagnostic_run_id
            ):
                raise ConflictError

            if (
                repositories.activity_evaluations.find_unresolved_by_skill_experience_id(
                    locked.id
                )
                is not None
            ):
                raise ConflictError

            catalog = self._curriculum.get_skill_content(skill_id)
            if catalog is None or catalog.id != skill_id or not catalog.v2_eligible:
                raise NotFoundError

            sequence = DiagnosticSequence.ordered(catalog)
            if len(items) != len(sequence) or any(
                item.competency_id != competency_id or item.activity_id != activity.id
                for item, (competency_id, activity) in zip(items, sequence, strict=True)
            ):
                raise ValidationError

            snapshots: list[CurriculumLearningActivitySnapshot] = []
            normalized: list[tuple[ActivityAnswer, ...]] = []
            for item in items:
                progress = repositories.competency_progresses.find_by_skill_experience_id_and_competency_id(
                    locked.id, item.competency_id
                )
                if progress is None or progress.skill_experience_id != locked.id:
                    raise ConflictError

                snapshot = self._curriculum.get_diagnostic_activity(item.activity_id)
                if (
                    snapshot is None
                    or snapshot.id != item.activity_id
                    or snapshot.competency_id != item.competency_id
                    or snapshot.activity_type != 'diagnostic'
                ):
                    raise NotFoundError

                if snapshot.diagnostic_revision != item.activity_revision:
                    raise ConflictError

                if not GetChoiceActivityUseCase.is_eligible(snapshot, diagnostic=True):
                    raise ValidationError

                snapshots.append(snapshot)
                normalized.append(
                    SubmitChoiceActivityUseCase.normalize_answers(
                        snapshot, item.answers
                    )
                )

            now = self._clock.now()
            for index, (item, key, snapshot, answers) in enumerate(
                zip(items, keys, snapshots, normalized, strict=True)
            ):
                attempt_id = self._identifiers.generate()
                run_id = self._identifiers.generate()
                repositories.activity_attempts.add(
                    ActivityAttempt.create(
                        id=attempt_id,
                        skill_experience_id=locked.id,
                        competency_id=item.competency_id,
                        activity_id=item.activity_id,
                        kind=ActivityAttemptKind.DIAGNOSTIC,
                        answers=answers,
                        submitted_at=now + timedelta(microseconds=index),
                        submission_key=key,
                        grading_snapshot=snapshot,
                        diagnostic_run_id=diagnostic_run_id,
                    )
                )
                repositories.activity_evaluations.add(
                    ActivityEvaluation.create(
                        id=self._identifiers.generate(),
                        attempt_id=attempt_id,
                        status=ActivityEvaluationStatus.PENDING,
                        parts=(),
                        started_at=now,
                        run_id=run_id,
                    )
                )
                repositories.events.add(
                    ActivitySubmissionRequestedEvent(
                        payload=ActivitySubmissionRequestedPayload(
                            attempt_id=attempt_id,
                            run_id=run_id,
                            skill_experience_id=locked.id,
                            activity_id=item.activity_id,
                            kind=ActivityAttemptKind.DIAGNOSTIC,
                            requested_at=now.astimezone(UTC)
                            .isoformat()
                            .replace('+00:00', 'Z'),
                        )
                    )
                )
            return DiagnosticBatchOutcome(replayed=False)

    @staticmethod
    def _validate_replay(
        repositories: LearningDatabaseRepositories,
        experience_id: str,
        diagnostic_run_id: str,
        items: tuple[DiagnosticSubmissionItem, ...],
        previous: tuple[ActivityAttempt | None, ...],
    ) -> None:
        run_attempts = repositories.activity_attempts.find_many_by_skill_experience_id_and_diagnostic_run_id(
            experience_id, diagnostic_run_id
        )
        if len(run_attempts) != len(items) or tuple(
            attempt.id for attempt in run_attempts
        ) != tuple(attempt.id for attempt in previous if attempt is not None):
            raise ConflictError

        for item, attempt in zip(items, previous, strict=True):
            if (
                attempt is None
                or attempt.kind is not ActivityAttemptKind.DIAGNOSTIC
                or attempt.diagnostic_run_id != diagnostic_run_id
                or attempt.competency_id != item.competency_id
                or attempt.activity_id != item.activity_id
                or attempt.grading_snapshot is None
                or attempt.grading_snapshot.diagnostic_revision
                != item.activity_revision
            ):
                raise ConflictError

            try:
                normalized = SubmitChoiceActivityUseCase.normalize_answers(
                    attempt.grading_snapshot, item.answers
                )
            except ValidationError as error:
                raise ConflictError from error
            if attempt.answers != normalized:
                raise ConflictError
