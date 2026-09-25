from datetime import UTC

from shifu.learning.core.domain.enums import ActivityEvaluationStatus
from shifu.learning.core.domain.events.activity_submission_requested_event import (
    ActivitySubmissionRequestedEvent,
    ActivitySubmissionRequestedPayload,
)
from shifu.learning.core.domain.structures import ChoiceAttemptDetail
from shifu.learning.core.interfaces import LearningDatabase
from shifu.shared.core.domain.errors import ConflictError, NotFoundError
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class RetryChoiceEvaluationUseCase:
    def __init__(
        self,
        learning_database: LearningDatabase,
        clock_provider: ClockProvider,
        identifier_provider: IdentifierProvider,
    ) -> None:
        self._learning_database = learning_database
        self._clock_provider = clock_provider
        self._identifier_provider = identifier_provider

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
            locked_experience = repositories.skill_experiences.find_by_id_for_update(
                experience.id
            )
            attempt = repositories.activity_attempts.find_by_id(attempt_id)
            if (
                locked_experience is None
                or attempt is None
                or attempt.id != attempt_id
                or attempt.skill_experience_id != locked_experience.id
                or attempt.competency_id != competency_id
                or attempt.activity_id != activity_id
                or attempt.grading_snapshot is None
            ):
                raise NotFoundError
            evaluation = (
                repositories.activity_evaluations.find_by_attempt_id_for_update(
                    attempt_id
                )
            )
            if evaluation is None:
                raise NotFoundError
            if evaluation.status is not ActivityEvaluationStatus.FAILED:
                raise ConflictError

            new_run_id = self._identifier_provider.generate()
            evaluation.retry(now, new_run_id)
            repositories.activity_evaluations.update(evaluation)
            repositories.events.add(
                ActivitySubmissionRequestedEvent(
                    payload=ActivitySubmissionRequestedPayload(
                        attempt_id=attempt.id,
                        run_id=new_run_id,
                        skill_experience_id=attempt.skill_experience_id,
                        activity_id=attempt.activity_id,
                        kind=attempt.kind,
                        requested_at=now.astimezone(UTC)
                        .isoformat()
                        .replace('+00:00', 'Z'),
                    )
                )
            )
            return ChoiceAttemptDetail(
                attempt_id=attempt.id,
                activity_id=attempt.activity_id,
                status=ActivityEvaluationStatus.PENDING,
                submitted_at=attempt.submitted_at,
                retry_allowed=False,
            )
