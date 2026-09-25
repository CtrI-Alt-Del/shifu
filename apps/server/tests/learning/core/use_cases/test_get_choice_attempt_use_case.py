from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import create_autospec

import pytest

from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.learning.core.domain.entities import (
    ActivityAttempt,
    ActivityEvaluation,
    CompetencyProgress,
)
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityEvaluationStatus,
    CompetencyProgressStatus,
)
from shifu.learning.core.domain.structures import (
    ChoiceEvaluationResult,
    MultipleSelectionAnswer,
    SingleChoiceAnswer,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases import GetChoiceAttemptUseCase
from shifu.shared.core.domain.errors import NotFoundError
from shifu.shared.core.domain.structures import (
    CurriculumChoiceActivitySnapshot,
    CurriculumChoiceOptionSnapshot,
    CurriculumChoicePartSnapshot,
    CurriculumChoiceQuestionSnapshot,
)
from shifu.shared.core.interfaces import ClockProvider, CurriculumContentProvider

NOW = datetime(2026, 9, 23, 12, tzinfo=UTC)
ACCOUNT_ID = 'account-1'
GOAL_ID = 'goal-1'
SKILL_ID = 'skill-1'
EXPERIENCE_ID = 'experience-1'
COMPETENCY_ID = 'competency-1'
ACTIVITY_ID = 'activity-1'


def snapshot() -> CurriculumChoiceActivitySnapshot:
    questions = tuple(
        CurriculumChoiceQuestionSnapshot(
            key=f'q{index}',
            kind='single_choice' if index == 1 else 'multiple_selection',
            prompt=f'Pergunta {index}?',
            options=(
                CurriculumChoiceOptionSnapshot(key='a', text='A', is_correct=True),
                CurriculumChoiceOptionSnapshot(key='b', text='B', is_correct=False),
                *(
                    (
                        CurriculumChoiceOptionSnapshot(
                            key='c', text='C', is_correct=True
                        ),
                    )
                    if index > 1
                    else ()
                ),
            ),
            correct_explanation='Explicação correta.',
            incorrect_explanation='Explicação incorreta.',
        )
        for index in range(1, 4)
    )
    return CurriculumChoiceActivitySnapshot(
        id=ACTIVITY_ID,
        competency_id=COMPETENCY_ID,
        difficulty='easy',
        title='Atividade',
        questions=questions,
        parts=tuple(
            CurriculumChoicePartSnapshot(
                question_key=f'q{index}',
                weight_percentage=Decimal(weight),
            )
            for index, weight in enumerate(('34', '33', '33'), 1)
        ),
    )


class TestGetChoiceAttemptUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(LearningDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.provider = create_autospec(CurriculumContentProvider, instance=True)
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = NOW
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
            answers=(
                SingleChoiceAnswer(question_key='q1', selected_option_key='b'),
                MultipleSelectionAnswer(
                    question_key='q2', selected_option_keys=('a', 'c')
                ),
                MultipleSelectionAnswer(question_key='q3', selected_option_keys=('a',)),
            ),
            submitted_at=NOW - timedelta(minutes=10),
            submission_key='submission-1',
            grading_snapshot=snapshot(),
        )
        self.evaluation = ActivityEvaluation.create(
            id='evaluation-1',
            attempt_id=self.attempt.id,
            status=ActivityEvaluationStatus.PENDING,
            parts=(),
            started_at=NOW - timedelta(minutes=4),
            run_id='run-1',
        )
        self.repositories.goals.find_by_id.return_value = self.goal
        self.repositories.skill_experiences.find_by_goal_id_and_skill_id.return_value = self.experience
        self.repositories.activity_attempts.find_by_id.return_value = self.attempt
        self.repositories.activity_evaluations.find_by_attempt_id_for_update.return_value = self.evaluation
        self.repositories.activity_attempts.find_many_by_skill_experience_id.return_value = [
            self.attempt
        ]
        self.repositories.activity_evaluations.find_many_by_attempt_ids.return_value = [
            self.evaluation
        ]
        self.repositories.competency_progresses.find_by_skill_experience_id_and_competency_id.return_value = CompetencyProgress(
            id='progress-1',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            content_released=True,
            created_at=NOW,
            updated_at=NOW,
            initial_progress=Decimal('0'),
            current_progress=Decimal('0'),
            status=CompetencyProgressStatus.LEARNING,
        )
        self.subject = GetChoiceAttemptUseCase(self.database, self.provider, self.clock)

    def test_should_mark_stale_pending_evaluation_failed_without_a_score(self) -> None:
        self.evaluation.started_at = NOW - timedelta(minutes=6)

        detail = self.subject.execute(
            ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID, self.attempt.id
        )

        assert detail.status is ActivityEvaluationStatus.FAILED
        assert detail.retry_allowed is True
        assert detail.score is None
        assert detail.questions == ()
        self.repositories.activity_evaluations.update.assert_called_once_with(
            self.evaluation
        )

    def test_should_hide_incorrect_keys_and_release_the_current_correct_answer(
        self,
    ) -> None:
        self.evaluation.status = ActivityEvaluationStatus.COMPLETED
        self.evaluation.score = Decimal('33')
        self.evaluation.completed_at = NOW
        self.evaluation.parts = (
            ChoiceEvaluationResult(
                question_key='q1',
                score=Decimal('0'),
                is_correct=False,
                explanation='Explicação incorreta.',
            ),
            ChoiceEvaluationResult(
                question_key='q2',
                score=Decimal('100'),
                is_correct=True,
                explanation='Explicação correta.',
            ),
            ChoiceEvaluationResult(
                question_key='q3',
                score=Decimal('0'),
                is_correct=False,
                explanation='Explicação incorreta.',
            ),
        )
        self.provider.get_skill_content.return_value = None

        detail = self.subject.execute(
            ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID, self.attempt.id
        )

        assert tuple(item.question_key for item in detail.questions) == (
            'q1',
            'q2',
            'q3',
        )
        assert detail.questions[0].selected_option_keys == ('b',)
        assert detail.questions[0].disclosed_correct_option_keys == ()
        assert detail.questions[1].disclosed_correct_option_keys == ('a', 'c')
        assert detail.questions[2].disclosed_correct_option_keys == ()
        assert detail.score == Decimal('33')

    def test_should_reject_another_accounts_attempt_as_private_absence(self) -> None:
        self.goal.account_id = 'another-account'

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

    def test_should_not_project_legacy_next_action_for_adaptive_result(self) -> None:
        self.experience.policy_id = 'learning-adaptive-v2'
        self.evaluation.status = ActivityEvaluationStatus.COMPLETED
        self.evaluation.score = Decimal('100')
        self.evaluation.completed_at = NOW
        self.evaluation.parts = tuple(
            ChoiceEvaluationResult(
                question_key=f'q{index}',
                score=Decimal('100'),
                is_correct=True,
                explanation='Explicação correta.',
            )
            for index in range(1, 4)
        )

        detail = self.subject.execute(
            ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID, self.attempt.id
        )

        assert detail.next_action is None
        self.provider.get_skill_content.assert_not_called()
