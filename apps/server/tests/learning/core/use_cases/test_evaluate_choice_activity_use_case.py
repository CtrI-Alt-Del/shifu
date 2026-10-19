from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import Mock, call, create_autospec, patch

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
    SkillExperienceStatus,
)
from shifu.learning.core.domain.errors import (
    EvaluationUnavailableError,
    InvalidAttemptError,
)
from shifu.learning.core.domain.structures import (
    AdaptiveCompetencyState,
    AdaptiveConceptState,
    AdaptivePolicyResult,
    CodeAnswer,
    CodeSubmittedFile,
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
    CodeCriterionDecision,
    CodeRubricDecisions,
    CurriculumActivitySnapshot,
    CurriculumChoiceActivitySnapshot,
    CurriculumChoiceConceptCriterionSnapshot,
    CurriculumChoiceOptionSnapshot,
    CurriculumChoicePartSnapshot,
    CurriculumChoiceQuestionSnapshot,
    CurriculumCompetencySnapshot,
    CurriculumConceptSnapshot,
    CurriculumSkillSnapshot,
)
from shifu.shared.core.interfaces import (
    CodeRubricAssessorProvider,
    CurriculumContentProvider,
)
from tests.learning.core.use_cases.test_preview_activity_question_feedback_use_case import (
    mixed_snapshot,
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
            concept_criteria=(
                CurriculumChoiceConceptCriterionSnapshot(
                    concept_id=f'concept-{index}',
                    criterion='Critério observável',
                    examples='Exemplo',
                    limits='Limite',
                    correct_score=Decimal('100'),
                    incorrect_score=Decimal('0'),
                ),
            ),
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
        required_concept_ids=('concept-1', 'concept-2', 'concept-3'),
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
        self.experience.status = SkillExperienceStatus.LEARNING
        self.curriculum = create_autospec(CurriculumContentProvider, instance=True)
        self.curriculum.get_skill_content.return_value = CurriculumSkillSnapshot(
            id=SKILL_ID,
            name='Habilidade',
            competencies=(
                CurriculumCompetencySnapshot(
                    id=COMPETENCY_ID,
                    skill_id=SKILL_ID,
                    name='Competência',
                    position=1,
                    concepts=tuple(
                        CurriculumConceptSnapshot(
                            id=f'concept-{index}',
                            competency_id=COMPETENCY_ID,
                            name=f'Conceito {index}',
                            position=index,
                            prerequisite_ids=(),
                            observation_criteria='Critério observável',
                        )
                        for index in range(1, 4)
                    ),
                    items=(
                        CurriculumActivitySnapshot(
                            id=ACTIVITY_ID,
                            title='Atividade',
                            activity_type='learning',
                            difficulty='hard',
                            position=1,
                            concept_ids=('concept-1', 'concept-2', 'concept-3'),
                            required_concept_ids=(
                                'concept-1',
                                'concept-2',
                                'concept-3',
                            ),
                            question_count_by_concept=(
                                ('concept-1', 1),
                                ('concept-2', 1),
                                ('concept-3', 1),
                            ),
                            maximum_evidence_by_concept=(
                                ('concept-1', 1),
                                ('concept-2', 1),
                                ('concept-3', 1),
                            ),
                            executable_concept_evidence=True,
                        ),
                    ),
                ),
            ),
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
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
            self.progress
        ]
        self.repositories.activity_evaluations.find_many_by_attempt_ids.return_value = [
            self.evaluation
        ]
        self.repositories.concept_observations.find_many_by_attempt_id.return_value = []
        self.repositories.concept_observations.find_many_by_skill_experience_id.return_value = []
        self.subject = EvaluateChoiceActivityUseCase(
            self.database,
            self.clock,
            self.curriculum,
        )

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
        assert self.evaluation.progress_after == Decimal(
            '66.66666666666666666666666667'
        )
        assert self.evaluation.effect_applied_at == NOW
        self.repositories.competency_progresses.update.assert_called_once_with(
            self.progress
        )
        self.repositories.events.add.assert_called_once()

        observations = self.repositories.concept_observations.add_many.call_args.args
        assert observations[:2] == (EXPERIENCE_ID, COMPETENCY_ID)
        assert tuple(item.concept_id for item in observations[2]) == (
            'concept-1',
            'concept-2',
            'concept-3',
        )
        assert tuple(item.question_scores for item in observations[2]) == (
            (Decimal('100'),),
            (Decimal('100'),),
            (Decimal('0'),),
        )
        assert all(item.attempt_id == self.attempt.id for item in observations[2])
        assert all(item.first_submitted_at == NOW for item in observations[2])
        assert all(item.completed_at == NOW for item in observations[2])
        event = self.repositories.events.add.call_args.args[0]
        assert event.payload.account_id == ACCOUNT_ID
        assert event.payload.attempt_id == self.attempt.id
        assert event.payload.evaluation_id == self.evaluation.id
        assert event.payload.score == '80'
        assert event.payload.evaluated_at == '2026-09-23T12:00:00Z'

    def test_should_apply_diagnostic_score_provisionally_using_frozen_rubric(
        self,
    ) -> None:
        self.experience.status = SkillExperienceStatus.DIAGNOSING
        self.experience.diagnostic_run_id = 'diagnostic-run'
        concept = CurriculumConceptSnapshot(
            id='concept',
            competency_id=COMPETENCY_ID,
            name='Conceito',
            position=1,
            prerequisite_ids=(),
            observation_criteria='Critério',
        )
        self.attempt = ActivityAttempt.create(
            id='diagnostic-attempt',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            activity_id=ACTIVITY_ID,
            kind=ActivityAttemptKind.DIAGNOSTIC,
            answers=(SingleChoiceAnswer(question_key='q', selected_option_key='a'),),
            submitted_at=NOW,
            submission_key='diagnostic-submission',
            diagnostic_run_id='diagnostic-run',
            grading_snapshot=CurriculumChoiceActivitySnapshot(
                id=ACTIVITY_ID,
                competency_id=COMPETENCY_ID,
                difficulty='easy',
                title='Diagnóstico',
                activity_type='diagnostic',
                required_concept_ids=('concept',),
                questions=(
                    CurriculumChoiceQuestionSnapshot(
                        key='q',
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
                        concept_criteria=(
                            CurriculumChoiceConceptCriterionSnapshot(
                                concept_id='concept',
                                criterion='Critério',
                                examples='Exemplos',
                                limits='Limites',
                                correct_score=Decimal('90'),
                                incorrect_score=Decimal('10'),
                            ),
                        ),
                    ),
                ),
                parts=(
                    CurriculumChoicePartSnapshot(
                        question_key='q', weight_percentage=Decimal('100')
                    ),
                ),
            ),
        )
        self.repositories.activity_attempts.find_by_id.return_value = self.attempt
        self.repositories.activity_attempts.find_many_by_skill_experience_id_and_diagnostic_run_id.return_value = [
            self.attempt
        ]
        self.evaluation = ActivityEvaluation.create(
            id='diagnostic-evaluation',
            attempt_id=self.attempt.id,
            status=ActivityEvaluationStatus.PENDING,
            parts=(),
            started_at=NOW,
            run_id='run-1',
        )
        self.repositories.activity_evaluations.find_by_attempt_id_for_update.return_value = self.evaluation
        self.repositories.activity_evaluations.find_many_by_attempt_ids.return_value = [
            self.evaluation
        ]
        self.repositories.concept_observations.find_many_by_attempt_id.return_value = []
        curriculum = create_autospec(CurriculumContentProvider, instance=True)
        curriculum.get_skill_content.return_value = CurriculumSkillSnapshot(
            id=SKILL_ID,
            name='Skill',
            competencies=(
                CurriculumCompetencySnapshot(
                    id=COMPETENCY_ID,
                    skill_id=SKILL_ID,
                    name='Competência',
                    position=1,
                    concepts=(concept,),
                    items=(),
                ),
            ),
        )
        self.subject = EvaluateChoiceActivityUseCase(
            self.database, self.clock, curriculum
        )

        self.subject.execute(self.attempt.id, 'run-1')

        assert self.evaluation.status is ActivityEvaluationStatus.COMPLETED
        assert self.evaluation.score == Decimal('100')
        assert self.evaluation.effect_applied_at is None
        assert self.progress.current_progress == Decimal('0')
        self.repositories.competency_progresses.update.assert_not_called()
        self.repositories.skill_experiences.update.assert_not_called()
        self.repositories.concept_observations.add_many.assert_called_once()
        observations = self.repositories.concept_observations.add_many.call_args.args[2]

        assert observations[0].concept_id == 'concept'
        assert observations[0].diagnostic is True
        self.repositories.events.add.assert_not_called()

    def test_should_ignore_stale_run_without_mutating_result_or_progress(self) -> None:
        self.subject.execute(self.attempt.id, 'stale-run')

        assert self.evaluation.status is ActivityEvaluationStatus.PENDING
        self.repositories.activity_evaluations.update.assert_not_called()
        self.repositories.competency_progresses.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_leave_mixed_attempt_pending_when_assessor_is_missing(self) -> None:
        self._set_mixed_attempt(react=True)

        with pytest.raises(EvaluationUnavailableError):
            self.subject.execute(self.attempt.id, 'run-1')

        assert self.evaluation.status is ActivityEvaluationStatus.PENDING
        self.repositories.activity_evaluations.update.assert_not_called()
        self.repositories.concept_observations.add_many.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_ignore_mixed_attempt_when_preflight_run_is_stale(self) -> None:
        self._set_mixed_attempt(react=True)
        assessor = create_autospec(CodeRubricAssessorProvider, instance=True)
        subject = EvaluateChoiceActivityUseCase(
            self.database, self.clock, self.curriculum, assessor
        )

        subject.execute(self.attempt.id, 'stale-run')

        assessor.assess.assert_not_called()
        self.clock.now.assert_not_called()
        self.repositories.skill_experiences.find_by_id_for_update.assert_not_called()
        self.repositories.activity_evaluations.update.assert_not_called()

    def test_should_ignore_mixed_attempt_when_preflight_evaluation_is_completed(
        self,
    ) -> None:
        self._set_mixed_attempt(react=True)
        self.evaluation.complete(Decimal('90'), NOW, ())
        assessor = create_autospec(CodeRubricAssessorProvider, instance=True)
        subject = EvaluateChoiceActivityUseCase(
            self.database, self.clock, self.curriculum, assessor
        )

        subject.execute(self.attempt.id, 'run-1')

        assessor.assess.assert_not_called()
        self.clock.now.assert_not_called()
        self.repositories.activity_evaluations.update.assert_not_called()

    def _set_mixed_attempt(self, *, react: bool = False) -> None:
        path = 'src/main.tsx' if react else 'src/main.js'
        self.attempt = ActivityAttempt.create(
            id='attempt-1',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            activity_id=ACTIVITY_ID,
            kind=ActivityAttemptKind.LEARNING,
            answers=(
                SingleChoiceAnswer(question_key='q1', selected_option_key='a'),
                SingleChoiceAnswer(question_key='q2', selected_option_key='a'),
                CodeAnswer(
                    question_key='q3',
                    files=(CodeSubmittedFile(path=path, content='submitted'),),
                ),
            ),
            submitted_at=NOW,
            submission_key='submission-1',
            grading_snapshot=mixed_snapshot(react=react),
        )
        self.repositories.activity_attempts.find_by_id.return_value = self.attempt
        self.repositories.activity_attempts.find_many_by_skill_experience_id.return_value = [
            self.attempt
        ]
        self.repositories.activity_evaluations.find_by_attempt_id.return_value = (
            self.evaluation
        )

    def test_should_grade_saved_mixed_project_with_unequal_question_weights(
        self,
    ) -> None:
        self.attempt = ActivityAttempt.create(
            id='attempt-1',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            activity_id=ACTIVITY_ID,
            kind=ActivityAttemptKind.LEARNING,
            answers=(
                SingleChoiceAnswer(question_key='q1', selected_option_key='a'),
                SingleChoiceAnswer(question_key='q2', selected_option_key='a'),
                CodeAnswer(
                    question_key='q3',
                    files=(CodeSubmittedFile(path='src/main.js', content='submitted'),),
                ),
            ),
            submitted_at=NOW,
            submission_key='submission-1',
            grading_snapshot=mixed_snapshot(),
        )
        self.repositories.activity_attempts.find_by_id.return_value = self.attempt
        self.repositories.activity_attempts.find_many_by_skill_experience_id.return_value = [
            self.attempt
        ]
        self.repositories.activity_evaluations.find_by_attempt_id.return_value = (
            self.evaluation
        )
        assessor = create_autospec(CodeRubricAssessorProvider, instance=True)
        assessor.assess.return_value = CodeRubricDecisions(
            criterion_levels=(CodeCriterionDecision(key='correctness', level=75),),
            concept_levels=(),
        )
        subject = EvaluateChoiceActivityUseCase(
            self.database,
            self.clock,
            self.curriculum,
            code_rubric_assessor_provider=assessor,
        )

        subject.execute(self.attempt.id, 'run-1')

        assert self.evaluation.status is ActivityEvaluationStatus.COMPLETED
        assert self.evaluation.score == Decimal(90)
        assert tuple(part.score for part in self.evaluation.parts) == (
            Decimal(100),
            Decimal(100),
            Decimal(75),
        )
        assert assessor.assess.call_args.args[0].project_files == (
            ('src/lib.js', 'fixed'),
            ('src/main.js', 'submitted'),
        )
        assert self.evaluation.effect_applied_at == NOW

    def test_should_grade_saved_react_project_and_preserve_frozen_result(
        self,
    ) -> None:
        self._set_mixed_attempt(react=True)
        assessor = create_autospec(CodeRubricAssessorProvider, instance=True)
        assessor.assess.return_value = CodeRubricDecisions(
            criterion_levels=(CodeCriterionDecision(key='correctness', level=50),),
            concept_levels=(),
        )
        subject = EvaluateChoiceActivityUseCase(
            self.database, self.clock, self.curriculum, assessor
        )

        subject.execute(self.attempt.id, 'run-1')

        assert self.evaluation.status is ActivityEvaluationStatus.COMPLETED
        assert self.evaluation.score == Decimal('80')
        assert tuple(part.question_key for part in self.evaluation.parts) == (
            'q1',
            'q2',
            'q3',
        )
        assert tuple(part.score for part in self.evaluation.parts) == (
            Decimal('100'),
            Decimal('100'),
            Decimal('50'),
        )
        assert assessor.assess.call_count == 1
        request = assessor.assess.call_args.args[0]
        assert request.project_files == (
            ('src/fixed.css', 'fixed'),
            ('src/main.tsx', 'submitted'),
        )
        assert self.evaluation.effect_applied_at == NOW
        self.repositories.activity_evaluations.update.assert_called_once_with(
            self.evaluation
        )
        self.repositories.events.add.assert_called_once()

    def test_should_reject_existing_observations_without_writing_duplicates(
        self,
    ) -> None:
        self.repositories.concept_observations.find_many_by_attempt_id.return_value = [
            Mock()
        ]

        with pytest.raises(InvalidAttemptError):
            self.subject.execute(self.attempt.id, 'run-1')

        self.repositories.concept_observations.add_many.assert_not_called()
        self.repositories.competency_progresses.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_complete_skill_with_persisted_summary_and_event(self) -> None:
        self.experience.started_at = datetime(2026, 9, 1, 12, tzinfo=UTC)
        self.progress.initial_progress = Decimal('25')
        self.progress.current_progress = Decimal('75')
        catalog = self.curriculum.get_skill_content.return_value

        # Exercise the completion boundary directly to cover its persisted summary.
        EvaluateChoiceActivityUseCase._complete_skill(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            self.repositories,
            self.goal,
            self.experience,
            catalog,
            [self.progress],
            NOW,
        )

        assert self.experience.status is SkillExperienceStatus.COMPLETED
        assert self.experience.completed_at == NOW
        summary = self.experience.completion_summary
        assert summary is not None
        assert summary.started_at == datetime(2026, 9, 1, 12, tzinfo=UTC)
        assert summary.completed_at == NOW
        assert summary.initial_progress == Decimal('25')
        assert summary.final_progress == Decimal('75')
        assert len(summary.competencies) == 1
        assert summary.competencies[0].competency_id == COMPETENCY_ID
        assert summary.competencies[0].initial_progress == Decimal('25')
        assert summary.competencies[0].final_progress == Decimal('75')
        self.repositories.skill_experiences.update.assert_called_once_with(
            self.experience
        )
        event = self.repositories.events.add.call_args.args[0]
        assert event.name == 'learning/skill-completed'
        assert event.payload.account_id == ACCOUNT_ID
        assert event.payload.goal_id == GOAL_ID
        assert event.payload.skill_experience_id == EXPERIENCE_ID
        assert event.payload.skill_id == SKILL_ID
        assert event.payload.initial_progress == '25'
        assert event.payload.final_progress == '75'
        assert event.payload.completed_at == '2026-09-23T12:00:00Z'

    def test_should_complete_skill_after_evaluating_last_required_activity(
        self,
    ) -> None:
        policy_result = AdaptivePolicyResult(
            concept_states=tuple(
                AdaptiveConceptState(
                    concept_id=f'concept-{index}',
                    initial_progress=Decimal('0'),
                    progress=Decimal('100'),
                    observed_difficulties=frozenset(),
                    distinct_activity_ids=frozenset({ACTIVITY_ID}),
                    hard_confirmation=True,
                    evidence_verification=False,
                    inconclusive_activity_ids=(),
                    current_contributions=(),
                )
                for index in range(1, 4)
            ),
            competency_states=(
                AdaptiveCompetencyState(
                    competency_id=COMPETENCY_ID,
                    progress=Decimal('100'),
                    partial_progress=Decimal('100'),
                    coverage_complete=True,
                    status=CompetencyProgressStatus.MASTERED,
                    mastered_at=NOW,
                    verification_cause=None,
                    verification_concept_id=None,
                    content_released=True,
                ),
            ),
            focus_competency_id=None,
            recommendation=None,
        )
        with patch(
            'shifu.learning.core.use_cases.evaluate_choice_activity_use_case.AdaptiveLearningPolicy.evaluate',
            return_value=policy_result,
        ) as evaluate_policy:
            self.subject.execute(self.attempt.id, 'run-1')

        evaluate_policy.assert_called_once()
        assert self.evaluation.status is ActivityEvaluationStatus.COMPLETED
        assert self.evaluation.score == Decimal('80')
        assert self.experience.status is SkillExperienceStatus.COMPLETED
        assert self.experience.completed_at == NOW
        summary = self.experience.completion_summary
        assert summary is not None
        assert summary.initial_progress == Decimal('0')
        assert summary.final_progress == Decimal('100')
        self.repositories.skill_experiences.update.assert_called_with(self.experience)
        event_names = tuple(
            item.args[0].name for item in self.repositories.events.add.call_args_list
        )
        assert event_names == (
            'learning/activity-evaluated',
            'learning/competency-mastered',
            'learning/skill-completed',
        )
        completion = self.repositories.events.add.call_args_list[-1].args[0]
        assert completion.payload.initial_progress == '0'
        assert completion.payload.final_progress == '100'

    def test_should_average_completed_competencies_and_preserve_unknown_baseline(
        self,
    ) -> None:
        self.progress.initial_progress = None
        self.progress.current_progress = Decimal('60')
        other_progress = CompetencyProgress(
            id='progress-2',
            skill_experience_id=EXPERIENCE_ID,
            competency_id='competency-2',
            content_released=True,
            created_at=NOW,
            updated_at=NOW,
            initial_progress=Decimal('40'),
            current_progress=Decimal('80'),
            status=CompetencyProgressStatus.LEARNING,
        )
        first = self.curriculum.get_skill_content.return_value.competencies[0]
        second = CurriculumCompetencySnapshot(
            id='competency-2',
            skill_id=SKILL_ID,
            name='Outra competência',
            position=2,
            concepts=(),
            items=(),
        )
        catalog = CurriculumSkillSnapshot(
            id=SKILL_ID,
            name='Habilidade',
            competencies=(first, second),
        )

        # Exercise the completion boundary directly to check aggregate arithmetic.
        EvaluateChoiceActivityUseCase._complete_skill(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            self.repositories,
            self.goal,
            self.experience,
            catalog,
            [self.progress, other_progress],
            NOW,
        )

        summary = self.experience.completion_summary
        assert summary is not None
        assert tuple(item.competency_id for item in summary.competencies) == (
            COMPETENCY_ID,
            'competency-2',
        )
        assert summary.competencies[0].initial_progress is None
        assert summary.competencies[0].final_progress == Decimal('60')
        assert summary.competencies[1].initial_progress == Decimal('40')
        assert summary.competencies[1].final_progress == Decimal('80')
        assert summary.initial_progress == Decimal('40')
        assert summary.final_progress == Decimal('70')
        assert summary.started_at == NOW
        event = self.repositories.events.add.call_args.args[0]
        assert event.payload.initial_progress == '40'
        assert event.payload.final_progress == '70'

    def test_should_record_unknown_initial_progress_when_no_baseline_exists(
        self,
    ) -> None:
        self.progress.initial_progress = None
        self.progress.current_progress = None
        catalog = self.curriculum.get_skill_content.return_value

        # Exercise the completion boundary directly to cover absent progress.
        EvaluateChoiceActivityUseCase._complete_skill(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            self.repositories,
            self.goal,
            self.experience,
            catalog,
            [self.progress],
            NOW,
        )

        summary = self.experience.completion_summary
        assert summary is not None
        assert summary.initial_progress is None
        assert summary.final_progress == Decimal('0')
        assert summary.competencies[0].final_progress == Decimal('0')
        event = self.repositories.events.add.call_args.args[0]
        assert event.payload.initial_progress == 'unknown'
        assert event.payload.final_progress == '0'

    def test_should_leave_mixed_attempt_pending_when_mandatory_criterion_inconclusive(
        self,
    ) -> None:
        self.attempt = ActivityAttempt.create(
            id='attempt-1',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            activity_id=ACTIVITY_ID,
            kind=ActivityAttemptKind.LEARNING,
            answers=(
                SingleChoiceAnswer(question_key='q1', selected_option_key='a'),
                SingleChoiceAnswer(question_key='q2', selected_option_key='a'),
                CodeAnswer(
                    question_key='q3',
                    files=(CodeSubmittedFile(path='src/main.js', content='submitted'),),
                ),
            ),
            submitted_at=NOW,
            submission_key='submission-1',
            grading_snapshot=mixed_snapshot(),
        )
        self.repositories.activity_attempts.find_by_id.return_value = self.attempt
        self.repositories.activity_evaluations.find_by_attempt_id.return_value = (
            self.evaluation
        )
        assessor = create_autospec(CodeRubricAssessorProvider, instance=True)
        assessor.assess.return_value = CodeRubricDecisions(
            criterion_levels=(
                CodeCriterionDecision(key='correctness', level='inconclusive'),
            ),
            concept_levels=(),
        )
        subject = EvaluateChoiceActivityUseCase(
            self.database, self.clock, code_rubric_assessor_provider=assessor
        )

        with pytest.raises(EvaluationUnavailableError):
            subject.execute(self.attempt.id, 'run-1')

        assert self.evaluation.status is ActivityEvaluationStatus.PENDING
        self.repositories.competency_progresses.update.assert_not_called()

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
