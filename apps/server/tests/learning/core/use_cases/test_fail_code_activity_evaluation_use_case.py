from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest
from shifu.fakers.learning.entities import SkillExperienceFaker
from shifu.learning.core.domain.entities import ActivityAttempt, ActivityEvaluation
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityEvaluationStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases import FailCodeActivityEvaluationUseCase

_ATTEMPT_ID = '01J000000000000000000000001'
_EXPERIENCE_ID = '01J000000000000000000000004'
_RUN_ID = '01J000000000000000000000002'
_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _attempt(
    *,
    kind: ActivityAttemptKind = ActivityAttemptKind.LEARNING,
    diagnostic_run_id: str | None = None,
) -> ActivityAttempt:
    return ActivityAttempt.create(
        id=_ATTEMPT_ID,
        skill_experience_id=_EXPERIENCE_ID,
        competency_id='competency-1',
        activity_id='activity-1',
        kind=kind,
        answers=(),
        submitted_at=_NOW,
        diagnostic_run_id=diagnostic_run_id,
    )


def _evaluation(
    status: ActivityEvaluationStatus = ActivityEvaluationStatus.PENDING,
) -> ActivityEvaluation:
    return ActivityEvaluation.create(
        id='01J000000000000000000000003',
        attempt_id=_ATTEMPT_ID,
        status=status,
        parts=(),
        started_at=_NOW,
        run_id=_RUN_ID,
    )


class TestFailCodeActivityEvaluationUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(LearningDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.attempt = _attempt()
        self.evaluation = _evaluation()
        self.repositories.activity_attempts.find_by_id.return_value = self.attempt
        self.repositories.activity_evaluations.find_by_attempt_id_for_update.return_value = self.evaluation
        self.subject = FailCodeActivityEvaluationUseCase(self.database)

    def test_should_fail_only_the_matching_pending_run(self) -> None:
        self.subject.execute(_ATTEMPT_ID, _RUN_ID)

        assert self.evaluation.status is ActivityEvaluationStatus.FAILED
        assert self.evaluation.failure_code == 'evaluation_failed'
        self.repositories.activity_evaluations.update.assert_called_once_with(
            self.evaluation
        )

    def test_should_ignore_a_missing_attempt(self) -> None:
        self.repositories.activity_attempts.find_by_id.return_value = None

        self.subject.execute(_ATTEMPT_ID, _RUN_ID)

        self.repositories.skill_experiences.find_by_id_for_update.assert_not_called()
        self.repositories.activity_evaluations.find_by_attempt_id_for_update.assert_not_called()
        self.repositories.activity_evaluations.update.assert_not_called()

    def test_should_ignore_a_stale_run(self) -> None:
        self.subject.execute(_ATTEMPT_ID, 'different-run')

        assert self.evaluation.status is ActivityEvaluationStatus.PENDING
        self.repositories.activity_evaluations.update.assert_not_called()

    def test_should_ignore_an_already_terminal_evaluation(self) -> None:
        self.evaluation.fail('already-failed')
        self.repositories.activity_evaluations.find_by_attempt_id_for_update.return_value = self.evaluation

        self.subject.execute(_ATTEMPT_ID, _RUN_ID)

        self.repositories.activity_evaluations.update.assert_not_called()

    def test_should_fail_a_diagnostic_run_that_is_still_active(self) -> None:
        self.attempt = _attempt(
            kind=ActivityAttemptKind.DIAGNOSTIC,
            diagnostic_run_id=_RUN_ID,
        )
        self.repositories.activity_attempts.find_by_id.return_value = self.attempt
        experience = SkillExperienceFaker.fake(
            id=_EXPERIENCE_ID,
            goal_id='goal-1',
            skill_id='skill-1',
        )
        experience.status = SkillExperienceStatus.DIAGNOSING
        experience.diagnostic_run_id = _RUN_ID
        self.repositories.skill_experiences.find_by_id_for_update.return_value = (
            experience
        )

        self.subject.execute(_ATTEMPT_ID, _RUN_ID)

        self.repositories.skill_experiences.find_by_id_for_update.assert_called_once_with(
            _EXPERIENCE_ID
        )
        assert self.evaluation.status is ActivityEvaluationStatus.FAILED
        self.repositories.activity_evaluations.update.assert_called_once_with(
            self.evaluation
        )

    def test_should_not_fail_a_diagnostic_run_without_an_active_experience(
        self,
    ) -> None:
        self.attempt = _attempt(
            kind=ActivityAttemptKind.DIAGNOSTIC,
            diagnostic_run_id=_RUN_ID,
        )
        self.repositories.activity_attempts.find_by_id.return_value = self.attempt
        self.repositories.skill_experiences.find_by_id_for_update.return_value = None

        self.subject.execute(_ATTEMPT_ID, _RUN_ID)

        self.repositories.activity_evaluations.find_by_attempt_id_for_update.assert_not_called()
        self.repositories.activity_evaluations.update.assert_not_called()

    def test_should_not_fail_a_diagnostic_run_when_its_run_id_was_replaced(
        self,
    ) -> None:
        self.attempt = _attempt(
            kind=ActivityAttemptKind.DIAGNOSTIC,
            diagnostic_run_id='previous-run',
        )
        self.repositories.activity_attempts.find_by_id.return_value = self.attempt
        experience = SkillExperienceFaker.fake(
            id=_EXPERIENCE_ID,
            goal_id='goal-1',
            skill_id='skill-1',
        )
        experience.status = SkillExperienceStatus.DIAGNOSING
        experience.diagnostic_run_id = _RUN_ID
        self.repositories.skill_experiences.find_by_id_for_update.return_value = (
            experience
        )

        self.subject.execute(_ATTEMPT_ID, _RUN_ID)

        self.repositories.activity_evaluations.find_by_attempt_id_for_update.assert_not_called()
        self.repositories.activity_evaluations.update.assert_not_called()
