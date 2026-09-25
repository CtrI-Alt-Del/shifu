from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import create_autospec

import pytest

from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.learning.core.domain.entities import ActivityAttempt, ActivityEvaluation
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityEvaluationStatus,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases import RetryChoiceEvaluationUseCase
from shifu.shared.core.domain.errors import ConflictError, NotFoundError
from shifu.shared.core.domain.structures import (
    CurriculumChoiceActivitySnapshot,
    CurriculumChoiceOptionSnapshot,
    CurriculumChoicePartSnapshot,
    CurriculumChoiceQuestionSnapshot,
)
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider

NOW = datetime(2026, 9, 23, 12, tzinfo=UTC)
ACCOUNT_ID = 'account-1'
GOAL_ID = 'goal-1'
SKILL_ID = 'skill-1'
EXPERIENCE_ID = 'experience-1'
COMPETENCY_ID = 'competency-1'
ACTIVITY_ID = 'activity-1'


class TestRetryChoiceEvaluationUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(LearningDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.clock = create_autospec(ClockProvider, instance=True)
        self.ids = create_autospec(IdentifierProvider, instance=True)
        self.clock.now.return_value = NOW
        self.ids.generate.return_value = 'run-2'
        self.goal = GoalFaker.fake(id=GOAL_ID, account_id=ACCOUNT_ID)
        self.experience = SkillExperienceFaker.fake(
            id=EXPERIENCE_ID, goal_id=GOAL_ID, skill_id=SKILL_ID
        )
        self.attempt = ActivityAttempt.create(
            id='attempt-1',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            activity_id=ACTIVITY_ID,
            kind=ActivityAttemptKind.LEARNING,
            answers=(),
            submitted_at=NOW,
            submission_key='submission-1',
            grading_snapshot=CurriculumChoiceActivitySnapshot(
                id=ACTIVITY_ID,
                competency_id=COMPETENCY_ID,
                difficulty='easy',
                title='Atividade',
                questions=(
                    CurriculumChoiceQuestionSnapshot(
                        key='q1',
                        kind='single_choice',
                        prompt='Pergunta?',
                        options=(
                            CurriculumChoiceOptionSnapshot(
                                key='a', text='A', is_correct=True
                            ),
                            CurriculumChoiceOptionSnapshot(
                                key='b', text='B', is_correct=False
                            ),
                        ),
                        correct_explanation='Correta.',
                        incorrect_explanation='Incorreta.',
                    ),
                ),
                parts=(
                    CurriculumChoicePartSnapshot(
                        question_key='q1', weight_percentage=Decimal('100')
                    ),
                ),
            ),
        )
        self.evaluation = ActivityEvaluation.create(
            id='evaluation-1',
            attempt_id=self.attempt.id,
            status=ActivityEvaluationStatus.FAILED,
            parts=(),
            started_at=NOW,
            failure_code='evaluation_failed',
            run_id='run-1',
        )
        self.repositories.goals.find_by_id.return_value = self.goal
        self.repositories.skill_experiences.find_by_goal_id_and_skill_id.return_value = self.experience
        self.repositories.skill_experiences.find_by_id_for_update.return_value = (
            self.experience
        )
        self.repositories.activity_attempts.find_by_id.return_value = self.attempt
        self.repositories.activity_evaluations.find_by_attempt_id_for_update.return_value = self.evaluation
        self.subject = RetryChoiceEvaluationUseCase(self.database, self.clock, self.ids)

    def test_should_retry_same_attempt_with_a_new_run_and_outbox_event(self) -> None:
        detail = self.subject.execute(
            ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID, self.attempt.id
        )

        assert detail.attempt_id == self.attempt.id
        assert detail.status is ActivityEvaluationStatus.PENDING
        assert self.evaluation.run_id == 'run-2'
        assert self.evaluation.failure_code is None
        self.repositories.activity_evaluations.update.assert_called_once_with(
            self.evaluation
        )
        event = self.repositories.events.add.call_args.args[0]
        assert event.payload.attempt_id == self.attempt.id
        assert event.payload.run_id == 'run-2'

    def test_should_reject_retry_when_evaluation_is_not_failed(self) -> None:
        self.evaluation.status = ActivityEvaluationStatus.PENDING

        with pytest.raises(ConflictError):
            self.subject.execute(
                ACCOUNT_ID,
                GOAL_ID,
                SKILL_ID,
                COMPETENCY_ID,
                ACTIVITY_ID,
                self.attempt.id,
            )

        self.repositories.events.add.assert_not_called()

    def test_should_not_reveal_attempt_from_another_account(self) -> None:
        self.repositories.goals.find_by_id.return_value = None

        with pytest.raises(NotFoundError):
            self.subject.execute(
                ACCOUNT_ID,
                GOAL_ID,
                SKILL_ID,
                COMPETENCY_ID,
                ACTIVITY_ID,
                self.attempt.id,
            )

        self.repositories.activity_attempts.find_by_id.assert_not_called()
