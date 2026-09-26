from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import Mock, call, create_autospec

import pytest

from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.learning.core.domain.entities import (
    ActivityAttempt,
    ActivityEvaluation,
    CompetencyProgress,
    SkillExperience,
)
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityEvaluationStatus,
    CompetencyProgressStatus,
)
from shifu.learning.core.domain.structures import (
    MultipleSelectionAnswer,
    SingleChoiceAnswer,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases import EvaluateChoiceActivityUseCase
from shifu.shared.core.interfaces import ClockProvider
from shifu.shared.core.domain.structures import (
    CurriculumChoiceActivitySnapshot,
    CurriculumChoiceOptionSnapshot,
    CurriculumChoicePartSnapshot,
    CurriculumChoiceQuestionSnapshot,
)

NOW = datetime(2026, 9, 23, 12, tzinfo=UTC)
ACCOUNT_ID = 'account-1'
GOAL_ID = 'goal-1'
SKILL_ID = 'skill-1'
EXPERIENCE_ID = 'experience-1'
COMPETENCY_ID = 'competency-1'
ACTIVITY_ID = 'activity-1'


def grading_snapshot() -> CurriculumChoiceActivitySnapshot:
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
            correct_explanation='Resposta correta.',
            incorrect_explanation='Resposta incorreta.',
        )
        for index in range(1, 4)
    )
    return CurriculumChoiceActivitySnapshot(
        id=ACTIVITY_ID,
        competency_id=COMPETENCY_ID,
        difficulty='hard',
        title='Atividade',
        questions=questions,
        parts=tuple(
            CurriculumChoicePartSnapshot(
                question_key=f'q{index}',
                weight_percentage=Decimal(weight),
            )
            for index, weight in enumerate(('50', '30', '20'), 1)
        ),
    )


class TestEvaluateChoiceActivityUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(LearningDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
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
                SingleChoiceAnswer(question_key='q1', selected_option_key='a'),
                MultipleSelectionAnswer(
                    question_key='q2', selected_option_keys=('c', 'a')
                ),
                MultipleSelectionAnswer(question_key='q3', selected_option_keys=('a',)),
            ),
            submitted_at=NOW,
            submission_key='submission-1',
            grading_snapshot=grading_snapshot(),
        )
        self.evaluation = ActivityEvaluation.create(
            id='evaluation-1',
            attempt_id=self.attempt.id,
            status=ActivityEvaluationStatus.PENDING,
            parts=(),
            started_at=NOW,
            run_id='run-1',
        )
        self.progress = CompetencyProgress(
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
        self.repositories.activity_attempts.find_by_id.return_value = self.attempt
        self.repositories.activity_evaluations.find_by_attempt_id_for_update.return_value = self.evaluation
        self.repositories.skill_experiences.find_by_id_for_update.return_value = (
            self.experience
        )
        self.repositories.goals.find_by_id.return_value = self.goal
        self.repositories.competency_progresses.find_by_skill_experience_id_and_competency_id.return_value = self.progress
        self.repositories.activity_attempts.find_many_by_skill_experience_id.return_value = [
            self.attempt
        ]
        self.repositories.activity_evaluations.find_many_by_attempt_ids.return_value = [
            self.evaluation
        ]
        self.subject = EvaluateChoiceActivityUseCase(self.database, self.clock)

    def test_should_score_exact_sets_and_apply_weighted_result_once(self) -> None:
        self.subject.execute(self.attempt.id, 'run-1')

        assert self.evaluation.status is ActivityEvaluationStatus.COMPLETED
        assert self.evaluation.score == Decimal('80')
        assert tuple(part.score for part in self.evaluation.parts) == (
            Decimal('100'),
            Decimal('100'),
            Decimal('0'),
        )
        assert self.evaluation.progress_before == Decimal('0')
        assert self.evaluation.progress_after == Decimal('24.0')
        assert self.evaluation.effect_applied_at == NOW
        self.repositories.competency_progresses.update.assert_called_once_with(
            self.progress
        )
        self.repositories.events.add.assert_called_once()

    def test_should_ignore_stale_run_without_mutating_result_or_progress(self) -> None:
        self.subject.execute(self.attempt.id, 'stale-run')

        assert self.evaluation.status is ActivityEvaluationStatus.PENDING
        self.repositories.activity_evaluations.update.assert_not_called()
        self.repositories.competency_progresses.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_lock_experience_before_evaluation(self) -> None:
        calls = Mock()

        def lock_experience(_experience_id: str) -> SkillExperience:
            calls.experience()
            return self.experience

        def lock_evaluation(_attempt_id: str) -> ActivityEvaluation:
            calls.evaluation()
            return self.evaluation

        self.repositories.skill_experiences.find_by_id_for_update.side_effect = (
            lock_experience
        )
        self.repositories.activity_evaluations.find_by_attempt_id_for_update.side_effect = lock_evaluation

        self.subject.execute(self.attempt.id, 'run-1')

        assert calls.mock_calls[:2] == [call.experience(), call.evaluation()]

    def test_should_ignore_missing_experience_before_locking_evaluation(self) -> None:
        self.repositories.skill_experiences.find_by_id_for_update.return_value = None

        self.subject.execute(self.attempt.id, 'run-1')

        self.repositories.activity_evaluations.find_by_attempt_id_for_update.assert_not_called()
        self.repositories.activity_evaluations.update.assert_not_called()
        self.repositories.events.add.assert_not_called()
