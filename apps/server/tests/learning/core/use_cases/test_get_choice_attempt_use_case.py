from datetime import UTC, datetime, timedelta
from tests.learning.core.use_cases.test_preview_activity_question_feedback_use_case import (
    integrated_question,
    mixed_snapshot,
)
from dataclasses import replace
from decimal import Decimal
from unittest.mock import create_autospec

from shifu.fakers.shared.curriculum_pair_matching_question_snapshot_faker import (
    CurriculumPairMatchingQuestionSnapshotFaker,
)

import pytest

from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.fakers.shared.curriculum_fill_blanks_activity_snapshot_faker import (
    CurriculumFillBlanksActivitySnapshotFaker,
)
from shifu.learning.core.domain.entities import (
    ActivityAttempt,
    ActivityEvaluation,
    CompetencyProgress,
)
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityEvaluationStatus,
    CompetencyProgressStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.structures import (
    ChoiceEvaluationResult,
    ChoiceResultDetail,
    CodeAnswer,
    CodeResultDetail,
    CodeCriterionResult,
    CodeConceptObservationResult,
    CodeRubricResult,
    CodeSubmittedFile,
    FillBlanksAnswer,
    FillBlanksEvaluationResult,
    FillBlanksExpectedBlank,
    FillBlanksPlacement,
    FillBlanksResultDetail,
    MultipleSelectionAnswer,
    PairMatchingAnswer,
    PairMatchingEvaluationResult,
    PairMatchingResultDetail,
    PairMatchingSelection,
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
    CurriculumCodeInconclusiveCommentSnapshot,
    CurriculumCodeRubricCommentSnapshot,
    CurriculumCodeRubricCriterionSnapshot,
    CurriculumCodeRubricPartSnapshot,
    CurriculumLearningActivitySnapshot,
    CurriculumReactInitialFileSnapshot,
    CurriculumReactQuestionSnapshot,
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

    @pytest.mark.parametrize('missing', ('experience', 'attempt', 'evaluation'))
    def test_should_hide_missing_owned_history_before_any_mutation(
        self, missing: str
    ) -> None:
        if missing == 'experience':
            self.repositories.skill_experiences.find_by_goal_id_and_skill_id.return_value = None
        elif missing == 'attempt':
            self.repositories.activity_attempts.find_by_id.return_value = None
        else:
            self.repositories.activity_evaluations.find_by_attempt_id_for_update.return_value = None

        with pytest.raises(NotFoundError):
            self.subject.execute(
                ACCOUNT_ID,
                GOAL_ID,
                SKILL_ID,
                COMPETENCY_ID,
                ACTIVITY_ID,
                self.attempt.id,
            )

        self.repositories.activity_evaluations.update.assert_not_called()
        self.provider.get_skill_content.assert_not_called()

    def test_should_release_frozen_choice_keys_when_competency_is_mastered(
        self,
    ) -> None:
        self.evaluation.status = ActivityEvaluationStatus.COMPLETED
        self.evaluation.score = Decimal(0)
        self.evaluation.completed_at = NOW
        self.evaluation.parts = tuple(
            ChoiceEvaluationResult(
                question_key=f'q{index}',
                score=Decimal(0),
                is_correct=False,
                explanation='Revisão',
            )
            for index in range(1, 4)
        )
        progress = self.repositories.competency_progresses.find_by_skill_experience_id_and_competency_id.return_value
        assert isinstance(progress, CompetencyProgress)
        progress.status = CompetencyProgressStatus.MASTERED

        detail = self.subject.execute(
            ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID, self.attempt.id
        )

        assert tuple(
            item.disclosed_correct_option_keys
            for item in detail.questions
            if isinstance(item, ChoiceResultDetail)
        ) == (
            ('a',),
            ('a', 'c'),
            ('a', 'c'),
        )
        self.repositories.activity_evaluations.update.assert_not_called()
        self.provider.get_skill_content.assert_not_called()

    def _complete_evaluation_and_experience(self) -> None:
        self.evaluation.status = ActivityEvaluationStatus.COMPLETED
        self.evaluation.score = Decimal(100)
        self.evaluation.completed_at = NOW
        self.experience.status = SkillExperienceStatus.COMPLETED

    def _other_attempt(
        self, attempt_id: str, kind: ActivityAttemptKind, submitted_at: datetime
    ) -> ActivityAttempt:
        return ActivityAttempt.create(
            id=attempt_id,
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            activity_id=ACTIVITY_ID,
            kind=kind,
            answers=(SingleChoiceAnswer(question_key='q1', selected_option_key='a'),),
            submitted_at=submitted_at,
            submission_key=f'submission-{attempt_id}',
            grading_snapshot=snapshot(),
        )

    def test_should_mark_the_latest_learning_attempt_of_a_completed_skill_as_completing(
        self,
    ) -> None:
        self._complete_evaluation_and_experience()
        earlier = self._other_attempt(
            'attempt-earlier',
            ActivityAttemptKind.LEARNING,
            NOW - timedelta(minutes=30),
        )
        review = self._other_attempt(
            'attempt-review',
            ActivityAttemptKind.REVIEW,
            NOW + timedelta(minutes=5),
        )
        self.repositories.activity_attempts.find_many_by_skill_experience_id.return_value = [
            earlier,
            self.attempt,
            review,
        ]

        detail = self.subject.execute(
            ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID, self.attempt.id
        )

        assert detail.completes_skill is True

    def test_should_not_mark_an_earlier_learning_attempt_as_completing(self) -> None:
        self._complete_evaluation_and_experience()
        later = self._other_attempt(
            'attempt-later',
            ActivityAttemptKind.LEARNING,
            NOW - timedelta(minutes=2),
        )
        self.repositories.activity_attempts.find_many_by_skill_experience_id.return_value = [
            self.attempt,
            later,
        ]

        detail = self.subject.execute(
            ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID, self.attempt.id
        )

        assert detail.completes_skill is False

    def test_should_not_mark_a_review_attempt_as_completing(self) -> None:
        self._complete_evaluation_and_experience()
        review = self._other_attempt(
            'attempt-review', ActivityAttemptKind.REVIEW, NOW - timedelta(minutes=1)
        )
        review_evaluation = ActivityEvaluation.create(
            id='evaluation-review',
            attempt_id=review.id,
            status=ActivityEvaluationStatus.PENDING,
            parts=(),
            started_at=NOW - timedelta(minutes=1),
            run_id='run-review',
        )
        review_evaluation.status = ActivityEvaluationStatus.COMPLETED
        review_evaluation.score = Decimal(80)
        review_evaluation.completed_at = NOW
        self.repositories.activity_attempts.find_by_id.return_value = review
        self.repositories.activity_evaluations.find_by_attempt_id_for_update.return_value = review_evaluation
        self.repositories.activity_attempts.find_many_by_skill_experience_id.return_value = [
            self.attempt,
            review,
        ]

        detail = self.subject.execute(
            ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID, review.id
        )

        assert detail.completes_skill is False

    def test_should_not_mark_a_learning_attempt_while_the_skill_is_still_learning(
        self,
    ) -> None:
        self._complete_evaluation_and_experience()
        self.experience.status = SkillExperienceStatus.LEARNING

        detail = self.subject.execute(
            ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID, self.attempt.id
        )

        assert detail.completes_skill is False

    def test_should_not_mark_an_attempt_whose_evaluation_is_pending(self) -> None:
        self.experience.status = SkillExperienceStatus.COMPLETED

        detail = self.subject.execute(
            ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID, self.attempt.id
        )

        assert detail.status is ActivityEvaluationStatus.PENDING
        assert detail.completes_skill is False

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
        assert isinstance(detail.questions[0], ChoiceResultDetail)
        assert isinstance(detail.questions[1], ChoiceResultDetail)
        assert isinstance(detail.questions[2], ChoiceResultDetail)
        assert detail.questions[0].selected_option_keys == ('b',)
        assert detail.questions[0].disclosed_correct_option_keys == ()
        assert detail.questions[1].disclosed_correct_option_keys == ('a', 'c')
        assert detail.questions[2].disclosed_correct_option_keys == ()
        assert detail.score == Decimal('33')

    @pytest.mark.parametrize('integrated', (False, True), ids=('react', 'integrated'))
    def test_should_preserve_react_kind_in_pending_and_completed_results(
        self, integrated: bool
    ) -> None:
        original = snapshot()
        react_question = CurriculumReactQuestionSnapshot(
            key='q3',
            prompt='Build a React component',
            initial_files=(
                CurriculumReactInitialFileSnapshot(
                    path='src/App.jsx', content='initial', editable=True
                ),
                CurriculumReactInitialFileSnapshot(
                    path='src/style.css', content='frozen stylesheet', editable=False
                ),
            ),
            entrypoint='src/App.jsx',
            fixed_dependencies=(),
            permitted_commands=(),
            concept_criteria=(),
            additional_file_policy=None,
        )
        criterion = CurriculumCodeRubricCriterionSnapshot(
            key='behavior',
            name='Behavior',
            description='Counter behavior',
            weight_percentage=100,
            required=True,
            fixed_comments=tuple(
                CurriculumCodeRubricCommentSnapshot(
                    id=f'level-{level}', level=level, text=f'Level {level}'
                )
                for level in (0, 25, 50, 75, 100)
            ),
            inconclusive_comment=CurriculumCodeInconclusiveCommentSnapshot(
                id='unknown', text='Inconclusive'
            ),
        )
        code_question = (
            integrated_question(react_question) if integrated else react_question
        )
        grading_snapshot = CurriculumLearningActivitySnapshot(
            id=ACTIVITY_ID,
            competency_id=COMPETENCY_ID,
            difficulty='easy',
            title='React activity',
            questions=(*original.questions[:2], code_question),
            parts=(
                *original.parts[:2],
                CurriculumCodeRubricPartSnapshot(
                    question_key='q3',
                    weight_percentage=original.parts[2].weight_percentage,
                    criteria=(criterion,),
                ),
            ),
            required_concept_ids=(),
            activity_type='learning',
            schema_version=1,
            revision='revision-react-1',
        )
        self.attempt = ActivityAttempt.create(
            id='attempt-react',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            activity_id=ACTIVITY_ID,
            kind=ActivityAttemptKind.LEARNING,
            answers=(
                CodeAnswer(
                    question_key='q3',
                    files=(
                        *(
                            (
                                CodeSubmittedFile(
                                    path='routes/api.js', content='saved api'
                                ),
                            )
                            if integrated
                            else ()
                        ),
                        CodeSubmittedFile(path='src/App.jsx', content='updated'),
                        CodeSubmittedFile(
                            path='src/Badge.jsx', content='new component'
                        ),
                    ),
                    kind=code_question.kind,
                ),
            ),
            submitted_at=NOW - timedelta(minutes=10),
            submission_key='submission-react',
            grading_snapshot=grading_snapshot,
        )
        self.repositories.activity_attempts.find_by_id.return_value = self.attempt
        self.repositories.activity_attempts.find_many_by_skill_experience_id.return_value = [
            self.attempt
        ]

        pending = self.subject.execute(
            ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID, self.attempt.id
        )
        assert len(pending.questions) == 1
        assert isinstance(pending.questions[0], CodeResultDetail)
        assert pending.questions[0].kind == code_question.kind
        assert pending.status is ActivityEvaluationStatus.PENDING
        assert pending.retry_allowed is False
        assert pending.score is None
        assert pending.questions[0].prompt == 'Build a React component'
        assert pending.questions[0].score is None
        assert pending.questions[0].criterion_results == ()
        assert pending.questions[0].concept_observations == ()
        assert tuple(
            (file.path, file.content) for file in pending.questions[0].submitted_files
        ) == (
            *((('routes/api.js', 'saved api'),) if integrated else ()),
            ('src/App.jsx', 'updated'),
            ('src/Badge.jsx', 'new component'),
            ('src/style.css', 'frozen stylesheet'),
        )

        self.evaluation.status = ActivityEvaluationStatus.COMPLETED
        self.evaluation.completed_at = NOW
        self.evaluation.score = Decimal(75)
        self.evaluation.progress_before = Decimal(20)
        self.evaluation.progress_after = Decimal(65)
        self.evaluation.status_before = CompetencyProgressStatus.LEARNING
        self.evaluation.status_after = CompetencyProgressStatus.LEARNING
        criterion_result = CodeCriterionResult(
            key='behavior',
            weight_percentage=100,
            level=75,
            comment_id='level-75',
            comment='Level 75',
        )
        concept_observation = CodeConceptObservationResult(
            concept_id='concept-react', level=75, observation_id='observation-75'
        )
        self.evaluation.parts = (
            CodeRubricResult(
                question_key='q3',
                score=Decimal(75),
                criterion_results=(criterion_result,),
                concept_observations=(concept_observation,),
            ),
        )
        completed = self.subject.execute(
            ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID, self.attempt.id
        )
        assert len(completed.questions) == 1
        assert isinstance(completed.questions[0], CodeResultDetail)
        assert completed.questions[0].kind == code_question.kind
        assert completed.status is ActivityEvaluationStatus.COMPLETED
        assert completed.retry_allowed is False
        assert completed.score == Decimal(75)
        assert completed.progress_before == Decimal(20)
        assert completed.progress_after == Decimal(65)
        assert completed.status_before is CompetencyProgressStatus.LEARNING
        assert completed.status_after is CompetencyProgressStatus.LEARNING
        assert completed.questions[0].prompt == 'Build a React component'
        assert completed.questions[0].score == Decimal(75)
        assert completed.questions[0].criterion_results == (criterion_result,)
        assert completed.questions[0].concept_observations == (concept_observation,)
        assert (
            completed.questions[0].submitted_files
            == pending.questions[0].submitted_files
        )

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

    def test_should_release_only_correct_keys_from_later_completed_attempt(
        self,
    ) -> None:
        self.evaluation.status = ActivityEvaluationStatus.COMPLETED
        self.evaluation.score = Decimal(33)
        self.evaluation.completed_at = NOW - timedelta(minutes=5)
        self.evaluation.parts = (
            ChoiceEvaluationResult(
                question_key='q1',
                score=Decimal(0),
                is_correct=False,
                explanation='Explicação incorreta.',
            ),
            ChoiceEvaluationResult(
                question_key='q2',
                score=Decimal(100),
                is_correct=True,
                explanation='Explicação correta.',
            ),
            ChoiceEvaluationResult(
                question_key='q3',
                score=Decimal(0),
                is_correct=False,
                explanation='Explicação incorreta.',
            ),
        )
        later = ActivityAttempt.create(
            id='attempt-later',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            activity_id=ACTIVITY_ID,
            kind=ActivityAttemptKind.LEARNING,
            answers=(SingleChoiceAnswer(question_key='q1', selected_option_key='a'),),
            submitted_at=NOW - timedelta(minutes=2),
            submission_key='submission-later',
            grading_snapshot=snapshot(),
        )
        later_evaluation = ActivityEvaluation.create(
            id='evaluation-later',
            attempt_id=later.id,
            status=ActivityEvaluationStatus.PENDING,
            parts=(),
            started_at=NOW - timedelta(minutes=2),
            run_id='run-later',
        )
        later_evaluation.status = ActivityEvaluationStatus.COMPLETED
        later_evaluation.completed_at = NOW
        later_evaluation.score = Decimal(100)
        later_evaluation.parts = (
            ChoiceEvaluationResult(
                question_key='q1',
                score=Decimal(100),
                is_correct=True,
                explanation='Explicação correta.',
            ),
        )
        self.repositories.activity_attempts.find_many_by_skill_experience_id.return_value = [
            self.attempt,
            later,
        ]
        self.repositories.activity_evaluations.find_many_by_attempt_ids.return_value = [
            self.evaluation,
            later_evaluation,
        ]

        detail = self.subject.execute(
            ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID, self.attempt.id
        )

        assert tuple(item.question_key for item in detail.questions) == (
            'q1',
            'q2',
            'q3',
        )
        first, second, third = detail.questions
        assert isinstance(first, ChoiceResultDetail)
        assert isinstance(second, ChoiceResultDetail)
        assert isinstance(third, ChoiceResultDetail)
        assert first.selected_option_keys == ('b',)
        assert first.disclosed_correct_option_keys == ('a',)
        assert second.selected_option_keys == ('a', 'c')
        assert second.disclosed_correct_option_keys == ('a', 'c')
        assert third.selected_option_keys == ('a',)
        assert third.disclosed_correct_option_keys == ()
        self.repositories.activity_attempts.find_many_by_skill_experience_id.assert_called_once_with(
            EXPERIENCE_ID
        )
        self.repositories.activity_evaluations.find_many_by_attempt_ids.assert_called_once_with(
            (self.attempt.id, later.id)
        )

    def _fill_result(
        self, correct_keys: tuple[str, ...], score: str
    ) -> FillBlanksEvaluationResult:
        return FillBlanksEvaluationResult(
            question_key='fill-1',
            score=Decimal(score),
            is_correct=len(correct_keys) == 3,
            correct_blank_keys=correct_keys,
            blank_count=3,
            explanation='Almost there. Review the verb forms.',
        )

    def _complete_fill_attempt(
        self,
        pairs: tuple[tuple[str, str], ...],
        result: FillBlanksEvaluationResult,
        *,
        attempt_id: str = 'attempt-1',
        submitted_at_offset: timedelta = timedelta(minutes=-10),
    ) -> tuple[ActivityAttempt, ActivityEvaluation]:
        attempt = ActivityAttempt.create(
            id=attempt_id,
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            activity_id=ACTIVITY_ID,
            kind=ActivityAttemptKind.LEARNING,
            answers=(
                FillBlanksAnswer(
                    question_key='fill-1',
                    placements=tuple(
                        FillBlanksPlacement(blank_key=blank, word_key=word)
                        for blank, word in pairs
                    ),
                ),
                SingleChoiceAnswer(question_key='q1', selected_option_key='a'),
                SingleChoiceAnswer(question_key='q2', selected_option_key='b'),
            ),
            submitted_at=NOW + submitted_at_offset,
            submission_key=f'submission-{attempt_id}',
            grading_snapshot=CurriculumFillBlanksActivitySnapshotFaker.fake(
                activity_id=ACTIVITY_ID, competency_id=COMPETENCY_ID
            ),
        )
        evaluation = ActivityEvaluation.create(
            id=f'evaluation-{attempt_id}',
            attempt_id=attempt.id,
            status=ActivityEvaluationStatus.PENDING,
            parts=(),
            started_at=NOW,
            run_id=f'run-{attempt_id}',
        )
        evaluation.status = ActivityEvaluationStatus.COMPLETED
        evaluation.completed_at = NOW
        evaluation.score = Decimal(50)
        evaluation.parts = (
            result,
            ChoiceEvaluationResult(
                question_key='q1', score=Decimal(100), is_correct=True, explanation='ok'
            ),
            ChoiceEvaluationResult(
                question_key='q2', score=Decimal(100), is_correct=True, explanation='ok'
            ),
        )
        return attempt, evaluation

    def _show(
        self, *entries: tuple[ActivityAttempt, ActivityEvaluation]
    ) -> FillBlanksResultDetail:
        self.attempt = entries[0][0]
        self.repositories.activity_attempts.find_by_id.return_value = self.attempt
        self.repositories.activity_evaluations.find_by_attempt_id_for_update.return_value = entries[
            0
        ][1]
        self.repositories.activity_attempts.find_many_by_skill_experience_id.return_value = [
            attempt for attempt, _ in entries
        ]
        self.repositories.activity_evaluations.find_many_by_attempt_ids.return_value = [
            evaluation for _, evaluation in entries
        ]
        detail = self.subject.execute(
            ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID, self.attempt.id
        )
        first = detail.questions[0]
        assert isinstance(first, FillBlanksResultDetail)
        return first

    EXPECTED = (
        FillBlanksExpectedBlank(blank_key='b1', accepted_words=('goes', 'walks')),
        FillBlanksExpectedBlank(blank_key='b2', accepted_words=('does',)),
        FillBlanksExpectedBlank(blank_key='b3', accepted_words=('day',)),
    )

    def test_should_show_the_submitted_fill_without_the_expected_words_before_release(
        self,
    ) -> None:
        pairs = (('b1', 'w1'), ('b2', 'w6'), ('b3', 'w2'))
        entry = self._complete_fill_attempt(pairs, self._fill_result(('b1',), '33.33'))

        fill = self._show(entry)

        assert fill.kind == 'fill_blanks'
        assert fill.question_key == 'fill-1'
        assert fill.content_language == 'en'
        assert fill.placements == tuple(
            FillBlanksPlacement(blank_key=blank, word_key=word) for blank, word in pairs
        )
        assert (fill.score, fill.is_correct) == (Decimal('33.33'), False)
        assert (fill.correct_blank_count, fill.blank_count) == (1, 3)
        assert fill.explanation == 'Almost there. Review the verb forms.'
        assert fill.disclosed_expected_blanks == ()
        assert [word.key for word in fill.bank] == ['w4', 'w6', 'w3', 'w1', 'w5', 'w2']
        assert not hasattr(fill, 'correct_blank_keys')

    def test_should_release_the_expected_words_when_the_fill_is_fully_correct(
        self,
    ) -> None:
        pairs = (('b1', 'w1'), ('b2', 'w3'), ('b3', 'w4'))
        entry = self._complete_fill_attempt(
            pairs, self._fill_result(('b1', 'b2', 'b3'), '100')
        )

        assert self._show(entry).disclosed_expected_blanks == self.EXPECTED

    def test_should_release_the_expected_words_after_a_later_fully_correct_attempt(
        self,
    ) -> None:
        wrong = (('b1', 'w1'), ('b2', 'w6'), ('b3', 'w2'))
        first = self._complete_fill_attempt(wrong, self._fill_result(('b1',), '33.33'))
        right = (('b1', 'w1'), ('b2', 'w3'), ('b3', 'w4'))
        later = self._complete_fill_attempt(
            right,
            self._fill_result(('b1', 'b2', 'b3'), '100'),
            attempt_id='attempt-later',
            submitted_at_offset=timedelta(minutes=-2),
        )

        assert self._show(first, later).disclosed_expected_blanks == self.EXPECTED

    def test_should_keep_the_expected_words_hidden_after_a_later_wrong_or_pending_attempt(
        self,
    ) -> None:
        wrong = (('b1', 'w1'), ('b2', 'w6'), ('b3', 'w2'))
        first = self._complete_fill_attempt(wrong, self._fill_result(('b1',), '33.33'))
        still_wrong = self._complete_fill_attempt(
            wrong,
            self._fill_result(('b2',), '33.33'),
            attempt_id='attempt-wrong',
            submitted_at_offset=timedelta(minutes=-4),
        )
        pending_attempt, pending_evaluation = self._complete_fill_attempt(
            (('b1', 'w1'), ('b2', 'w3'), ('b3', 'w4')),
            self._fill_result(('b1', 'b2', 'b3'), '100'),
            attempt_id='attempt-pending',
            submitted_at_offset=timedelta(minutes=-2),
        )
        pending_evaluation.status = ActivityEvaluationStatus.PENDING

        fill = self._show(first, still_wrong, (pending_attempt, pending_evaluation))

        assert fill.disclosed_expected_blanks == ()

    def test_should_release_the_expected_words_when_the_competency_is_mastered(
        self,
    ) -> None:
        pairs = (('b1', 'w1'), ('b2', 'w6'), ('b3', 'w2'))
        entry = self._complete_fill_attempt(pairs, self._fill_result(('b1',), '33.33'))
        progress = self.repositories.competency_progresses.find_by_skill_experience_id_and_competency_id.return_value
        assert isinstance(progress, CompetencyProgress)
        progress.status = CompetencyProgressStatus.MASTERED

        assert self._show(entry).disclosed_expected_blanks == self.EXPECTED

    def test_should_not_project_legacy_next_action_for_adaptive_result(self) -> None:
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

    _KEY = (
        PairMatchingSelection(word_key='word-0', translation_key='translation-0'),
        PairMatchingSelection(word_key='word-1', translation_key='translation-1'),
        PairMatchingSelection(word_key='word-2', translation_key='translation-2'),
    )

    def _use_pair_attempt(
        self,
        order: tuple[int, ...],
        outcome: str,
        correct: int,
        *,
        attempt_id: str = 'attempt-1',
        submitted_at: datetime | None = None,
    ) -> tuple[ActivityAttempt, ActivityEvaluation]:
        base = mixed_snapshot()
        grading = replace(
            base,
            questions=(
                base.questions[0],
                base.questions[1],
                CurriculumPairMatchingQuestionSnapshotFaker.fake('q3'),
            ),
            parts=(
                base.parts[0],
                base.parts[1],
                CurriculumChoicePartSnapshot(
                    question_key='q3', weight_percentage=Decimal(40)
                ),
            ),
        )
        attempt = ActivityAttempt.create(
            id=attempt_id,
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            activity_id=ACTIVITY_ID,
            kind=ActivityAttemptKind.LEARNING,
            answers=(
                SingleChoiceAnswer(question_key='q1', selected_option_key='a'),
                SingleChoiceAnswer(question_key='q2', selected_option_key='a'),
                PairMatchingAnswer(
                    question_key='q3',
                    pairs=tuple(
                        PairMatchingSelection(
                            word_key=f'word-{word_index}',
                            translation_key=f'translation-{translation_index}',
                        )
                        for word_index, translation_index in enumerate(order)
                    ),
                ),
            ),
            submitted_at=submitted_at or NOW - timedelta(minutes=10),
            submission_key=f'submission-{attempt_id}',
            grading_snapshot=grading,
        )
        evaluation = ActivityEvaluation.create(
            id=f'evaluation-{attempt_id}',
            attempt_id=attempt.id,
            status=ActivityEvaluationStatus.PENDING,
            parts=(),
            started_at=NOW - timedelta(minutes=9),
            run_id=f'run-{attempt_id}',
        )
        evaluation.parts = (
            ChoiceEvaluationResult(
                question_key='q1',
                score=Decimal(100),
                is_correct=True,
                explanation='Correct',
            ),
            ChoiceEvaluationResult(
                question_key='q2',
                score=Decimal(100),
                is_correct=True,
                explanation='Correct',
            ),
            PairMatchingEvaluationResult(
                question_key='q3',
                score={
                    0: Decimal('0.00'),
                    1: Decimal('33.33'),
                    2: Decimal('66.67'),
                    3: Decimal('100.00'),
                }[correct],
                correct_pair_count=correct,
                total_pair_count=3,
                outcome=outcome,  # type: ignore[arg-type]
                explanation={
                    'full': 'Todos os pares estao corretos.',
                    'partial': 'Alguns pares estao corretos.',
                    'incorrect': 'Nenhum par esta correto.',
                }[outcome],
            ),
        )
        evaluation.status = ActivityEvaluationStatus.COMPLETED
        evaluation.score = Decimal(80)
        evaluation.completed_at = NOW
        self.repositories.activity_attempts.find_by_id.return_value = attempt
        self.repositories.activity_evaluations.find_by_attempt_id_for_update.return_value = evaluation
        self.repositories.activity_attempts.find_many_by_skill_experience_id.return_value = [
            attempt
        ]
        self.repositories.activity_evaluations.find_many_by_attempt_ids.return_value = [
            evaluation
        ]
        return attempt, evaluation

    def _pair_detail(self, attempt: ActivityAttempt) -> PairMatchingResultDetail:
        detail = self.subject.execute(
            ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID, attempt.id
        )
        pair_details = [
            item
            for item in detail.questions
            if isinstance(item, PairMatchingResultDetail)
        ]
        assert len(pair_details) == 1
        return pair_details[0]

    @pytest.mark.parametrize(
        ('order', 'outcome', 'correct'),
        (((0, 2, 1), 'partial', 1), ((1, 2, 0), 'incorrect', 0)),
    )
    def test_should_hide_expected_pairs_for_partial_and_incorrect_pair_answers(
        self, order: tuple[int, ...], outcome: str, correct: int
    ) -> None:
        attempt, _ = self._use_pair_attempt(order, outcome, correct)

        detail = self._pair_detail(attempt)

        assert detail.kind == 'pair_matching'
        assert detail.outcome == outcome
        assert detail.correct_pair_count == correct
        assert detail.total_pair_count == 3
        assert (
            detail.score
            == {
                0: Decimal('0.00'),
                1: Decimal('33.33'),
                2: Decimal('66.67'),
                3: Decimal('100.00'),
            }[correct]
        )
        assert detail.submitted_pairs == attempt.answers[2].pairs  # type: ignore[union-attr]
        assert detail.disclosed_correct_pairs == ()

    def test_should_show_the_key_of_a_fully_correct_pair_answer(self) -> None:
        attempt, _ = self._use_pair_attempt((0, 1, 2), 'full', 3)

        detail = self._pair_detail(attempt)

        assert detail.outcome == 'full'
        assert detail.disclosed_correct_pairs == self._KEY

    def test_should_release_the_key_after_a_later_fully_correct_attempt(self) -> None:
        attempt, evaluation = self._use_pair_attempt((0, 2, 1), 'partial', 1)
        later_attempt, later_evaluation = self._use_pair_attempt(
            (0, 1, 2),
            'full',
            3,
            attempt_id='attempt-2',
            submitted_at=NOW - timedelta(minutes=5),
        )
        self.repositories.activity_attempts.find_by_id.return_value = attempt
        self.repositories.activity_evaluations.find_by_attempt_id_for_update.return_value = evaluation
        self.repositories.activity_attempts.find_many_by_skill_experience_id.return_value = [
            attempt,
            later_attempt,
        ]
        self.repositories.activity_evaluations.find_many_by_attempt_ids.return_value = [
            evaluation,
            later_evaluation,
        ]

        detail = self._pair_detail(attempt)

        assert detail.outcome == 'partial'
        assert detail.disclosed_correct_pairs == self._KEY

    def test_should_keep_the_key_hidden_after_a_later_partial_attempt(self) -> None:
        attempt, evaluation = self._use_pair_attempt((1, 2, 0), 'incorrect', 0)
        later_attempt, later_evaluation = self._use_pair_attempt(
            (0, 2, 1),
            'partial',
            1,
            attempt_id='attempt-2',
            submitted_at=NOW - timedelta(minutes=5),
        )
        self.repositories.activity_attempts.find_by_id.return_value = attempt
        self.repositories.activity_evaluations.find_by_attempt_id_for_update.return_value = evaluation
        self.repositories.activity_attempts.find_many_by_skill_experience_id.return_value = [
            attempt,
            later_attempt,
        ]
        self.repositories.activity_evaluations.find_many_by_attempt_ids.return_value = [
            evaluation,
            later_evaluation,
        ]

        detail = self._pair_detail(attempt)

        assert detail.disclosed_correct_pairs == ()

    def test_should_release_the_key_when_the_competency_is_mastered(self) -> None:
        attempt, _ = self._use_pair_attempt((1, 2, 0), 'incorrect', 0)
        progress = self.repositories.competency_progresses.find_by_skill_experience_id_and_competency_id.return_value
        assert isinstance(progress, CompetencyProgress)
        progress.status = CompetencyProgressStatus.MASTERED

        detail = self._pair_detail(attempt)

        assert detail.outcome == 'incorrect'
        assert detail.disclosed_correct_pairs == self._KEY
