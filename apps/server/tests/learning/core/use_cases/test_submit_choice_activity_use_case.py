from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import create_autospec

import pytest

from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.learning.core.domain.entities import CompetencyProgress
from shifu.learning.core.domain.enums import ActivityEvaluationStatus
from shifu.learning.core.domain.structures import (
    ChoiceAnswerSubmission,
    MultipleSelectionAnswer,
    SingleChoiceAnswer,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases import SubmitChoiceActivityUseCase
from shifu.shared.core.domain.errors import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from shifu.shared.core.domain.structures import (
    CurriculumChoiceActivitySnapshot,
    CurriculumChoiceOptionSnapshot,
    CurriculumChoicePartSnapshot,
    CurriculumChoiceQuestionSnapshot,
)
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumContentProvider,
    IdentifierProvider,
)

ACCOUNT_ID = 'account-1'
GOAL_ID = 'goal-1'
SKILL_ID = 'skill-1'
COMPETENCY_ID = 'competency-1'
EXPERIENCE_ID = 'experience-1'
ACTIVITY_ID = 'activity-1'
NOW = datetime(2026, 9, 23, 12, tzinfo=UTC)


def choice_snapshot() -> CurriculumChoiceActivitySnapshot:
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
            correct_explanation='Correta',
            incorrect_explanation='Incorreta',
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


def answers() -> tuple[ChoiceAnswerSubmission, ...]:
    return (
        ChoiceAnswerSubmission(question_key='q1', selected_option_keys=('a',)),
        ChoiceAnswerSubmission(question_key='q2', selected_option_keys=('c', 'a')),
        ChoiceAnswerSubmission(question_key='q3', selected_option_keys=('a',)),
    )


class TestSubmitChoiceActivityUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(LearningDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.provider = create_autospec(CurriculumContentProvider, instance=True)
        self.clock = create_autospec(ClockProvider, instance=True)
        self.ids = create_autospec(IdentifierProvider, instance=True)
        self.ids.generate.side_effect = ('attempt-1', 'evaluation-1', 'run-1')
        self.clock.now.return_value = NOW
        self.goal = GoalFaker.fake(id=GOAL_ID, account_id=ACCOUNT_ID)
        self.experience = SkillExperienceFaker.fake(
            id=EXPERIENCE_ID, goal_id=GOAL_ID, skill_id=SKILL_ID
        )
        self.progress = CompetencyProgress(
            id='progress-1',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            content_released=True,
            created_at=NOW,
            updated_at=NOW,
            initial_progress=Decimal('0'),
        )
        self.repositories.goals.find_by_id.return_value = self.goal
        self.repositories.skill_experiences.find_by_goal_id_and_skill_id.return_value = self.experience
        self.repositories.skill_experiences.find_by_id_for_update.return_value = (
            self.experience
        )
        self.repositories.competency_progresses.find_by_skill_experience_id_and_competency_id.return_value = self.progress
        self.repositories.activity_attempts.find_by_skill_experience_id_and_submission_key.return_value = None
        self.repositories.activity_evaluations.find_unresolved_by_skill_experience_id.return_value = None
        self.provider.get_choice_activity.return_value = choice_snapshot()
        self.subject = SubmitChoiceActivityUseCase(
            self.database, self.provider, self.clock, self.ids
        )

    def test_should_persist_one_immutable_attempt_evaluation_and_handoff(self) -> None:
        detail = self.subject.execute(
            ACCOUNT_ID,
            GOAL_ID,
            SKILL_ID,
            COMPETENCY_ID,
            ACTIVITY_ID,
            'submission-key',
            answers(),
        )

        assert detail.attempt.attempt_id == 'attempt-1'
        assert detail.attempt.status is ActivityEvaluationStatus.PENDING
        assert detail.replayed is False
        attempt = self.repositories.activity_attempts.add.call_args.args[0]
        assert attempt.answers == (
            SingleChoiceAnswer(question_key='q1', selected_option_key='a'),
            MultipleSelectionAnswer(question_key='q2', selected_option_keys=('c', 'a')),
            MultipleSelectionAnswer(question_key='q3', selected_option_keys=('a',)),
        )
        assert attempt.submission_key == 'submission-key'
        assert attempt.grading_snapshot.id == ACTIVITY_ID
        evaluation = self.repositories.activity_evaluations.add.call_args.args[0]
        assert evaluation.run_id == 'run-1'
        event = self.repositories.events.add.call_args.args[0]
        assert event.payload.attempt_id == attempt.id
        assert event.payload.run_id == evaluation.run_id

    def test_should_reject_incomplete_answers_without_writing(self) -> None:
        with pytest.raises(ValidationError):
            self.subject.execute(
                ACCOUNT_ID,
                GOAL_ID,
                SKILL_ID,
                COMPETENCY_ID,
                ACTIVITY_ID,
                'submission-key',
                answers()[:-1],
            )

        self.repositories.activity_attempts.add.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_reuse_matching_key_and_reject_different_payload(self) -> None:
        prior = self.repositories.activity_attempts.find_by_skill_experience_id_and_submission_key
        from shifu.learning.core.domain.entities import (
            ActivityAttempt,
            ActivityEvaluation,
        )
        from shifu.learning.core.domain.enums import ActivityAttemptKind

        attempt = ActivityAttempt.create(
            id='attempt-prior',
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
            submission_key='submission-key',
            grading_snapshot=choice_snapshot(),
        )
        evaluation = ActivityEvaluation.create(
            id='evaluation-prior',
            attempt_id=attempt.id,
            status=ActivityEvaluationStatus.PENDING,
            parts=(),
            started_at=NOW,
            run_id='run-prior',
        )
        prior.return_value = attempt
        self.repositories.activity_evaluations.find_by_attempt_id.return_value = (
            evaluation
        )
        replay = self.subject.execute(
            ACCOUNT_ID,
            GOAL_ID,
            SKILL_ID,
            COMPETENCY_ID,
            ACTIVITY_ID,
            'submission-key',
            answers(),
        )
        assert replay.attempt.attempt_id == attempt.id
        assert replay.replayed is True
        self.repositories.activity_attempts.add.assert_not_called()
        self.repositories.events.add.assert_not_called()

        with pytest.raises(ConflictError):
            self.subject.execute(
                ACCOUNT_ID,
                GOAL_ID,
                SKILL_ID,
                COMPETENCY_ID,
                ACTIVITY_ID,
                'submission-key',
                (
                    ChoiceAnswerSubmission(
                        question_key='q1', selected_option_keys=('b',)
                    ),
                    *answers()[1:],
                ),
            )

    def test_should_reject_multiple_keys_for_single_choice(self) -> None:
        with pytest.raises(ValidationError):
            self.subject.execute(
                ACCOUNT_ID,
                GOAL_ID,
                SKILL_ID,
                COMPETENCY_ID,
                ACTIVITY_ID,
                'submission-key',
                (
                    ChoiceAnswerSubmission(
                        question_key='q1', selected_option_keys=('a', 'b')
                    ),
                    *answers()[1:],
                ),
            )

        self.repositories.activity_attempts.add.assert_not_called()

    def test_should_reject_private_absence_without_curriculum_read(self) -> None:
        self.repositories.goals.find_by_id.return_value = None

        with pytest.raises(NotFoundError):
            self.subject.execute(
                ACCOUNT_ID,
                GOAL_ID,
                SKILL_ID,
                COMPETENCY_ID,
                ACTIVITY_ID,
                'key',
                answers(),
            )

        self.provider.get_choice_activity.assert_not_called()
