from dataclasses import replace
from datetime import UTC, datetime, timedelta
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
    ActivityDifficulty,
    ActivityEvaluationStatus,
    CompetencyProgressStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.errors import (
    EvaluationUnavailableError,
    InvalidAttemptError,
)
from shifu.learning.core.domain.events.competency_mastery_lost_event import (
    CompetencyMasteryLostEvent,
)
from shifu.learning.core.domain.structures import ConceptObservation
from shifu.learning.core.domain.structures import (
    CodeAnswer,
    CodeQuestionAssessmentDecisions,
    CodeSubmittedFile,
    MultipleSelectionAnswer,
    SingleChoiceAnswer,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases import EvaluateChoiceActivityUseCase
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
    ClockProvider,
    CurriculumContentProvider,
)
from tests.learning.core.use_cases.test_preview_activity_question_feedback_use_case import (
    mixed_snapshot,
)

NOW = datetime(2026, 9, 23, 12, tzinfo=UTC)
SUBMITTED_AT = NOW - timedelta(hours=5)
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
                    correct_score=Decimal(100),
                    incorrect_score=Decimal(0),
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
            submitted_at=SUBMITTED_AT,
            submission_key='submission-1',
            grading_snapshot=grading_snapshot(),
            time_zone='America/Sao_Paulo',
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
            initial_progress=Decimal(0),
            current_progress=Decimal(0),
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
        assert self.evaluation.score == Decimal(80)
        assert tuple(part.score for part in self.evaluation.parts) == (
            Decimal(100),
            Decimal(100),
            Decimal(0),
        )
        assert self.evaluation.progress_before == Decimal(0)
        assert self.evaluation.progress_after == Decimal(
            '66.66666666666666666666666667'
        )
        assert self.evaluation.effect_applied_at == NOW
        self.repositories.competency_progresses.update.assert_called_once_with(
            self.progress
        )
        self.repositories.events.add.assert_called_once()

        # Gamification dates the practice day from the attempt submission, not
        # from when the asynchronous evaluation finished.
        payload = self.repositories.events.add.call_args.args[0].payload
        assert payload.submitted_at == SUBMITTED_AT.astimezone(UTC).isoformat().replace(
            '+00:00', 'Z'
        )
        assert payload.time_zone == 'America/Sao_Paulo'
        assert payload.evaluated_at == NOW.astimezone(UTC).isoformat().replace(
            '+00:00', 'Z'
        )
        assert payload.submitted_at != payload.evaluated_at

    def test_should_complete_the_skill_when_all_required_concepts_are_mastered(
        self,
    ) -> None:
        observed_at = datetime(2026, 9, 20, 12, tzinfo=UTC)
        prior_observations = tuple(
            ConceptObservation(
                attempt_id=f'{concept_id}-{difficulty.value}',
                activity_id=f'{concept_id}-{difficulty.value}',
                concept_id=concept_id,
                difficulty=difficulty,
                first_submitted_at=observed_at,
                submitted_at=observed_at,
                completed_at=observed_at,
                question_scores=(Decimal(100),),
                diagnostic=True,
            )
            for concept_id in ('concept-1', 'concept-2', 'concept-3')
            for difficulty in (
                ActivityDifficulty.EASY,
                ActivityDifficulty.MEDIUM,
                ActivityDifficulty.HARD,
            )
        )
        self.repositories.concept_observations.find_many_by_skill_experience_id.return_value = prior_observations
        attempt = ActivityAttempt.create(
            id='attempt-complete-skill',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            activity_id=ACTIVITY_ID,
            kind=ActivityAttemptKind.LEARNING,
            answers=(
                SingleChoiceAnswer(question_key='q1', selected_option_key='a'),
                MultipleSelectionAnswer(
                    question_key='q2', selected_option_keys=('a', 'c')
                ),
                MultipleSelectionAnswer(
                    question_key='q3', selected_option_keys=('a', 'c')
                ),
            ),
            submitted_at=NOW,
            submission_key='submission-complete-skill',
            grading_snapshot=grading_snapshot(),
        )
        self.repositories.activity_attempts.find_by_id.return_value = attempt
        self.repositories.activity_attempts.find_many_by_skill_experience_id.return_value = [
            attempt
        ]

        self.subject.execute(attempt.id, 'run-1')

        assert self.experience.status is SkillExperienceStatus.COMPLETED
        assert self.experience.completion_summary is not None
        assert self.experience.completion_summary.initial_progress == Decimal(100)
        assert self.experience.completion_summary.final_progress == Decimal(100)
        assert self.repositories.skill_experiences.update.call_count == 2
        assert self.repositories.events.add.call_count == 3

    def test_should_use_the_initial_progress_when_current_progress_is_unknown(
        self,
    ) -> None:
        self.progress.initial_progress = Decimal(40)
        self.progress.current_progress = None

        self.subject.execute(self.attempt.id, 'run-1')

        assert self.evaluation.status is ActivityEvaluationStatus.COMPLETED
        self.repositories.competency_progresses.update.assert_called_once_with(
            self.progress
        )

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
                                correct_score=Decimal(90),
                                incorrect_score=Decimal(10),
                            ),
                        ),
                    ),
                ),
                parts=(
                    CurriculumChoicePartSnapshot(
                        question_key='q', weight_percentage=Decimal(100)
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
        assert self.evaluation.score == Decimal(100)
        assert self.evaluation.effect_applied_at is None
        assert self.progress.current_progress == Decimal(0)
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
        self.repositories.activity_evaluations.find_by_attempt_id.return_value = (
            self.evaluation
        )
        self.repositories.activity_attempts.find_many_by_skill_experience_id.return_value = [
            self.attempt
        ]
        self.repositories.activity_evaluations.find_by_attempt_id.return_value = (
            self.evaluation
        )
        decisions = CodeRubricDecisions(
            criterion_levels=(CodeCriterionDecision(key='correctness', level=75),),
            concept_levels=(),
        )
        subject = EvaluateChoiceActivityUseCase(
            self.database,
            self.clock,
            self.curriculum,
        )

        subject.execute(
            self.attempt.id,
            'run-1',
            code_decisions=(
                CodeQuestionAssessmentDecisions(question_key='q3', decisions=decisions),
            ),
        )

        assert self.evaluation.status is ActivityEvaluationStatus.COMPLETED
        assert self.evaluation.score == Decimal(90)
        assert tuple(part.score for part in self.evaluation.parts) == (
            Decimal(100),
            Decimal(100),
            Decimal(75),
        )
        assert self.evaluation.effect_applied_at == NOW

    def test_should_record_review_result_without_reapplying_learning_progress(
        self,
    ) -> None:
        self.experience.status = SkillExperienceStatus.COMPLETED
        self.attempt = ActivityAttempt.create(
            id='review-attempt',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            activity_id=ACTIVITY_ID,
            kind=ActivityAttemptKind.REVIEW,
            answers=(
                SingleChoiceAnswer(question_key='q1', selected_option_key='a'),
                SingleChoiceAnswer(question_key='q2', selected_option_key='a'),
                CodeAnswer(
                    question_key='q3',
                    files=(CodeSubmittedFile(path='src/main.js', content='submitted'),),
                ),
            ),
            submitted_at=NOW,
            submission_key='review-submission',
            grading_snapshot=mixed_snapshot(),
        )
        self.repositories.activity_attempts.find_by_id.return_value = self.attempt
        self.repositories.activity_evaluations.find_by_attempt_id.return_value = (
            self.evaluation
        )
        self.repositories.activity_evaluations.find_by_attempt_id_for_update.return_value = self.evaluation
        decisions = CodeRubricDecisions(
            criterion_levels=(CodeCriterionDecision(key='correctness', level=75),),
            concept_levels=(),
        )

        self.subject.execute(
            self.attempt.id,
            'run-1',
            code_decisions=(
                CodeQuestionAssessmentDecisions(question_key='q3', decisions=decisions),
            ),
        )

        assert self.evaluation.status is ActivityEvaluationStatus.COMPLETED
        assert self.evaluation.effect_applied_at == NOW
        self.repositories.competency_progresses.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

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
        decisions = CodeRubricDecisions(
            criterion_levels=(
                CodeCriterionDecision(key='correctness', level='inconclusive'),
            ),
            concept_levels=(),
        )
        subject = EvaluateChoiceActivityUseCase(self.database, self.clock)

        with pytest.raises(EvaluationUnavailableError):
            subject.execute(
                self.attempt.id,
                'run-1',
                code_decisions=(
                    CodeQuestionAssessmentDecisions(
                        question_key='q3', decisions=decisions
                    ),
                ),
            )

        assert self.evaluation.status is ActivityEvaluationStatus.PENDING
        self.repositories.competency_progresses.update.assert_not_called()

    def test_should_ignore_assessment_decisions_without_a_pending_evaluation(
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
        self.repositories.activity_evaluations.find_by_attempt_id.return_value = None
        decisions = CodeRubricDecisions(
            criterion_levels=(CodeCriterionDecision(key='correctness', level=75),),
            concept_levels=(),
        )

        self.subject.execute(
            self.attempt.id,
            'run-1',
            code_decisions=(
                CodeQuestionAssessmentDecisions(question_key='q3', decisions=decisions),
            ),
        )

        assert self.evaluation.status is ActivityEvaluationStatus.PENDING
        self.repositories.activity_evaluations.find_by_attempt_id_for_update.assert_not_called()
        self.repositories.activity_evaluations.update.assert_not_called()

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

    def test_should_ignore_a_missing_attempt_before_locking_experience(self) -> None:
        self.repositories.activity_attempts.find_by_id.return_value = None

        self.subject.execute('missing-attempt', 'run-1')

        self.repositories.skill_experiences.find_by_id_for_update.assert_not_called()
        self.repositories.activity_evaluations.find_by_attempt_id_for_update.assert_not_called()
        self.repositories.activity_evaluations.update.assert_not_called()

    def test_should_ignore_an_attempt_without_a_saved_rubric(self) -> None:
        self.attempt = ActivityAttempt.create(
            id='attempt-without-rubric',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            activity_id=ACTIVITY_ID,
            kind=ActivityAttemptKind.LEARNING,
            answers=(),
            submitted_at=NOW,
        )
        self.repositories.activity_attempts.find_by_id.return_value = self.attempt

        self.subject.execute(self.attempt.id, 'run-1')

        self.repositories.skill_experiences.find_by_id_for_update.assert_not_called()
        self.repositories.activity_evaluations.find_by_attempt_id_for_update.assert_not_called()
        self.repositories.activity_evaluations.update.assert_not_called()

    def test_should_ignore_evaluation_when_its_goal_is_missing(self) -> None:
        self.repositories.goals.find_by_id.return_value = None

        self.subject.execute(self.attempt.id, 'run-1')

        self.repositories.competency_progresses.find_by_skill_experience_id_and_competency_id.assert_not_called()
        self.repositories.activity_evaluations.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_ignore_evaluation_when_its_progress_row_is_missing(self) -> None:
        self.repositories.competency_progresses.find_by_skill_experience_id_and_competency_id.return_value = None

        with pytest.raises(InvalidAttemptError):
            self.subject.execute(self.attempt.id, 'run-1')

        self.repositories.activity_evaluations.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_ignore_an_invalidated_diagnostic_run_before_evaluation_lock(
        self,
    ) -> None:
        self.attempt = ActivityAttempt.create(
            id='stale-diagnostic-attempt',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            activity_id=ACTIVITY_ID,
            kind=ActivityAttemptKind.DIAGNOSTIC,
            answers=(),
            submitted_at=NOW,
            diagnostic_run_id='previous-diagnostic-run',
            grading_snapshot=grading_snapshot(),
        )
        self.experience.status = SkillExperienceStatus.DIAGNOSING
        self.experience.diagnostic_run_id = 'current-diagnostic-run'
        self.repositories.activity_attempts.find_by_id.return_value = self.attempt

        self.subject.execute(self.attempt.id, 'run-1')

        self.repositories.activity_evaluations.find_by_attempt_id_for_update.assert_not_called()
        self.repositories.activity_evaluations.update.assert_not_called()

    def test_should_reject_evaluation_when_current_curriculum_is_unavailable(
        self,
    ) -> None:
        subject = EvaluateChoiceActivityUseCase(self.database, self.clock)

        with pytest.raises(InvalidAttemptError):
            subject.execute(self.attempt.id, 'run-1')

        self.repositories.activity_evaluations.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_reject_evaluation_when_current_curriculum_does_not_match(
        self,
    ) -> None:
        self.curriculum.get_skill_content.return_value = CurriculumSkillSnapshot(
            id='another-skill', name='Outra', competencies=()
        )

        with pytest.raises(InvalidAttemptError):
            self.subject.execute(self.attempt.id, 'run-1')

        self.repositories.activity_evaluations.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_reject_observations_for_concepts_missing_from_current_curriculum(
        self,
    ) -> None:
        self.curriculum.get_skill_content.return_value = CurriculumSkillSnapshot(
            id=SKILL_ID,
            name='Skill sem os conceitos congelados',
            competencies=(),
        )

        with pytest.raises(InvalidAttemptError):
            self.subject.execute(self.attempt.id, 'run-1')

        self.repositories.activity_evaluations.update.assert_not_called()
        self.repositories.concept_observations.add_many.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_reject_when_a_competency_progress_row_is_missing(self) -> None:
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = []

        with pytest.raises(InvalidAttemptError):
            self.subject.execute(self.attempt.id, 'run-1')

        self.repositories.activity_evaluations.update.assert_not_called()
        self.repositories.concept_states.upsert_many.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_reject_learning_attempt_when_its_saved_activity_type_is_invalid(
        self,
    ) -> None:
        self.experience.status = SkillExperienceStatus.COMPLETED

        with pytest.raises(InvalidAttemptError):
            self.subject.execute(self.attempt.id, 'run-1')

        self.repositories.activity_evaluations.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_reject_diagnostic_attempt_with_a_learning_rubric(self) -> None:
        self.experience.status = SkillExperienceStatus.DIAGNOSING
        self.experience.diagnostic_run_id = 'diagnostic-run'
        self.attempt = ActivityAttempt.create(
            id='diagnostic-attempt',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            activity_id=ACTIVITY_ID,
            kind=ActivityAttemptKind.DIAGNOSTIC,
            answers=self.attempt.answers,
            submitted_at=NOW,
            submission_key='diagnostic-submission',
            diagnostic_run_id='diagnostic-run',
            grading_snapshot=grading_snapshot(),
        )
        self.repositories.activity_attempts.find_by_id.return_value = self.attempt

        with pytest.raises(InvalidAttemptError):
            self.subject.execute(self.attempt.id, 'run-1')

        self.repositories.activity_evaluations.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_reject_review_attempt_before_skill_completion(self) -> None:
        self.attempt = ActivityAttempt.create(
            id='review-attempt',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            activity_id=ACTIVITY_ID,
            kind=ActivityAttemptKind.REVIEW,
            answers=self.attempt.answers,
            submitted_at=NOW,
            submission_key='review-submission',
            grading_snapshot=grading_snapshot(),
        )
        self.repositories.activity_attempts.find_by_id.return_value = self.attempt

        with pytest.raises(InvalidAttemptError):
            self.subject.execute(self.attempt.id, 'run-1')

        self.repositories.activity_evaluations.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_reject_code_decisions_for_a_choice_attempt(self) -> None:
        decisions = CodeRubricDecisions(
            criterion_levels=(CodeCriterionDecision(key='correctness', level=75),),
            concept_levels=(),
        )

        with pytest.raises(EvaluationUnavailableError):
            self.subject.execute(
                self.attempt.id,
                'run-1',
                code_decisions=(
                    CodeQuestionAssessmentDecisions(
                        question_key='q3', decisions=decisions
                    ),
                ),
            )

        assert self.evaluation.status is ActivityEvaluationStatus.PENDING
        self.repositories.activity_evaluations.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

    @pytest.mark.parametrize(
        'answers',
        [
            (
                MultipleSelectionAnswer(question_key='q1', selected_option_keys=('a',)),
                *(
                    SingleChoiceAnswer(
                        question_key=f'q{index}', selected_option_key='a'
                    )
                    for index in (2, 3)
                ),
            ),
            (
                SingleChoiceAnswer(question_key='q1', selected_option_key='a'),
                SingleChoiceAnswer(question_key='q2', selected_option_key='a'),
                SingleChoiceAnswer(question_key='q3', selected_option_key='a'),
            ),
            (),
        ],
        ids=(
            'wrong-single-choice-kind',
            'wrong-multiple-selection-kind',
            'missing-answer',
        ),
    )
    def test_should_reject_choice_answers_that_do_not_match_the_saved_questions(
        self,
        answers: tuple[SingleChoiceAnswer | MultipleSelectionAnswer, ...],
    ) -> None:
        with pytest.raises(InvalidAttemptError):
            self.subject._score(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                answers, grading_snapshot()
            )

    def test_should_reject_missing_choice_or_code_results_before_observing_them(
        self,
    ) -> None:
        mixed = mixed_snapshot()

        with pytest.raises(InvalidAttemptError):
            self.subject._v2_observation_scores(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                (mixed.questions[0],), ()
            )
        with pytest.raises(InvalidAttemptError):
            self.subject._v2_observation_scores(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                (mixed.questions[-1],), ()
            )

    def test_should_reject_mixed_attempt_when_saved_answers_do_not_cover_all_questions(
        self,
    ) -> None:
        snapshot = mixed_snapshot()
        attempt = ActivityAttempt.create(
            id='incomplete-mixed-attempt',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            activity_id=ACTIVITY_ID,
            kind=ActivityAttemptKind.LEARNING,
            answers=(
                SingleChoiceAnswer(question_key='q1', selected_option_key='a'),
                CodeAnswer(
                    question_key='q3',
                    files=(CodeSubmittedFile(path='src/main.js', content='submitted'),),
                ),
            ),
            submitted_at=NOW,
            grading_snapshot=snapshot,
        )

        with pytest.raises(InvalidAttemptError):
            self.subject._score_mixed(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                attempt, ()
            )

    def test_should_grade_multiple_selection_in_a_mixed_activity(self) -> None:
        snapshot = mixed_snapshot()
        multiple_question = replace(snapshot.questions[1], kind='multiple_selection')
        saved_snapshot = replace(
            snapshot,
            questions=(snapshot.questions[0], multiple_question, snapshot.questions[2]),
        )
        self.attempt = ActivityAttempt.create(
            id='mixed-multiple-selection-attempt',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            activity_id=ACTIVITY_ID,
            kind=ActivityAttemptKind.LEARNING,
            answers=(
                SingleChoiceAnswer(question_key='q1', selected_option_key='a'),
                MultipleSelectionAnswer(question_key='q2', selected_option_keys=('a',)),
                CodeAnswer(
                    question_key='q3',
                    files=(CodeSubmittedFile(path='src/main.js', content='submitted'),),
                ),
            ),
            submitted_at=NOW,
            submission_key='mixed-multiple-selection-submission',
            grading_snapshot=saved_snapshot,
        )
        self.repositories.activity_attempts.find_by_id.return_value = self.attempt
        self.repositories.activity_evaluations.find_by_attempt_id.return_value = (
            self.evaluation
        )
        self.repositories.activity_attempts.find_many_by_skill_experience_id.return_value = [
            self.attempt
        ]
        decisions = CodeRubricDecisions(
            criterion_levels=(CodeCriterionDecision(key='correctness', level=75),),
            concept_levels=(),
        )

        self.subject.execute(
            self.attempt.id,
            'run-1',
            code_decisions=(
                CodeQuestionAssessmentDecisions(question_key='q3', decisions=decisions),
            ),
        )

        assert self.evaluation.status is ActivityEvaluationStatus.COMPLETED
        assert self.evaluation.parts[1].score == Decimal(100)

    def test_should_reject_non_code_answer_for_saved_code_question(self) -> None:
        snapshot = mixed_snapshot()
        attempt = ActivityAttempt.create(
            id='mixed-invalid-code-answer-attempt',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            activity_id=ACTIVITY_ID,
            kind=ActivityAttemptKind.LEARNING,
            answers=(
                SingleChoiceAnswer(question_key='q1', selected_option_key='a'),
                SingleChoiceAnswer(question_key='q2', selected_option_key='a'),
                SingleChoiceAnswer(question_key='q3', selected_option_key='a'),
            ),
            submitted_at=NOW,
            grading_snapshot=snapshot,
        )
        decisions = CodeRubricDecisions(
            criterion_levels=(CodeCriterionDecision(key='correctness', level=75),),
            concept_levels=(),
        )

        with pytest.raises(EvaluationUnavailableError):
            self.subject._score_mixed(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                attempt,
                (
                    CodeQuestionAssessmentDecisions(
                        question_key='q3', decisions=decisions
                    ),
                ),
            )

    def test_should_translate_invalid_code_decisions_to_unavailable_evaluation(
        self,
    ) -> None:
        self.attempt = ActivityAttempt.create(
            id='mixed-invalid-decisions-attempt',
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
            submission_key='mixed-invalid-decisions-submission',
            grading_snapshot=mixed_snapshot(),
        )
        self.repositories.activity_attempts.find_by_id.return_value = self.attempt
        self.repositories.activity_evaluations.find_by_attempt_id.return_value = (
            self.evaluation
        )
        decisions = CodeRubricDecisions(
            criterion_levels=(CodeCriterionDecision(key='unexpected', level=75),),
            concept_levels=(),
        )

        with pytest.raises(EvaluationUnavailableError):
            self.subject.execute(
                self.attempt.id,
                'run-1',
                code_decisions=(
                    CodeQuestionAssessmentDecisions(
                        question_key='q3', decisions=decisions
                    ),
                ),
            )

        assert self.evaluation.status is ActivityEvaluationStatus.PENDING
        self.repositories.activity_evaluations.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_emit_mastery_lost_event_when_progress_is_revoked(self) -> None:
        self.subject._publish_mastery_transition(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            repositories=self.repositories,
            goal=self.goal,
            experience=self.experience,
            competency_id=COMPETENCY_ID,
            progress=Decimal(50),
            status_before=CompetencyProgressStatus.MASTERED,
            status_after=CompetencyProgressStatus.LEARNING,
            mastered_at=None,
            evaluated_at='2026-09-23T12:00:00Z',
        )

        event = self.repositories.events.add.call_args.args[0]
        assert isinstance(event, CompetencyMasteryLostEvent)
        assert event.payload.competency_id == COMPETENCY_ID
        assert event.payload.progress == '50'

    def test_should_reject_replaying_an_attempt_that_already_has_observations(
        self,
    ) -> None:
        self.repositories.concept_observations.find_many_by_attempt_id.return_value = [
            object()
        ]

        with pytest.raises(InvalidAttemptError):
            self.subject.execute(self.attempt.id, 'run-1')

        self.repositories.activity_evaluations.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_reject_mixed_submission_without_code_decisions(self) -> None:
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

        with pytest.raises(EvaluationUnavailableError):
            self.subject.execute(self.attempt.id, 'run-1')

        self.repositories.competency_progresses.update.assert_not_called()
        self.repositories.activity_evaluations.update.assert_not_called()

    def test_should_address_every_collaborator_with_the_attempt_identity(self) -> None:
        """The orchestration reads each collaborator with identifiers taken from
        the attempt and its experience; passing the wrong one would silently
        evaluate somebody else's work."""
        self.subject.execute(self.attempt.id, 'run-1')

        self.repositories.activity_attempts.find_by_id.assert_called_with(
            self.attempt.id
        )
        self.repositories.skill_experiences.find_by_id_for_update.assert_called_once_with(
            self.attempt.skill_experience_id
        )
        self.repositories.activity_evaluations.find_by_attempt_id_for_update.assert_called_once_with(
            self.attempt.id
        )
        self.repositories.goals.find_by_id.assert_called_once_with(
            self.experience.goal_id
        )
        self.repositories.competency_progresses.find_by_skill_experience_id_and_competency_id.assert_called_once_with(
            self.experience.id, self.attempt.competency_id
        )
        self.curriculum.get_skill_content.assert_called_with(self.experience.skill_id)
        self.repositories.activity_evaluations.update.assert_called_once_with(
            self.evaluation
        )

    def test_should_publish_the_evaluated_event_with_the_attempt_identity(
        self,
    ) -> None:
        self.subject.execute(self.attempt.id, 'run-1')

        payload = self.repositories.events.add.call_args_list[0].args[0].payload
        assert payload.account_id == self.goal.account_id
        assert payload.goal_id == self.goal.id
        assert payload.skill_experience_id == self.experience.id
        assert payload.skill_id == self.experience.skill_id
        assert payload.competency_id == self.attempt.competency_id
        assert payload.activity_id == self.attempt.activity_id
        assert payload.attempt_id == self.attempt.id
        assert payload.evaluation_id == self.evaluation.id
        assert payload.kind is self.attempt.kind
        assert payload.score == str(self.evaluation.score)
        assert payload.evaluated_at == NOW.astimezone(UTC).isoformat().replace(
            '+00:00', 'Z'
        )

    def test_should_scope_adaptive_reads_to_the_locked_experience(self) -> None:
        self.subject.execute(self.attempt.id, 'run-1')

        self.repositories.competency_progresses.find_many_by_skill_experience_id.assert_called_with(
            self.experience.id
        )
        self.repositories.concept_observations.find_many_by_skill_experience_id.assert_called_with(
            self.experience.id
        )

    def test_should_stamp_the_evaluation_effect_with_the_injected_clock(self) -> None:
        self.subject.execute(self.attempt.id, 'run-1')

        assert self.evaluation.effect_applied_at == NOW
        assert self.evaluation.completed_at == NOW
        self.clock.now.assert_called()

    def test_should_publish_mastery_lost_with_the_competency_identity(self) -> None:
        """A competency that regresses out of mastery announces the loss, so
        Gamification can revoke what it rewarded."""
        self.progress.status = CompetencyProgressStatus.MASTERED

        self.subject.execute(self.attempt.id, 'run-1')

        lost = next(
            call.args[0]
            for call in self.repositories.events.add.call_args_list
            if call.args[0].name == 'learning/competency-mastery-lost'
        )
        assert lost.payload.account_id == self.goal.account_id
        assert lost.payload.goal_id == self.goal.id
        assert lost.payload.skill_experience_id == self.experience.id
        assert lost.payload.skill_id == self.experience.skill_id
        assert lost.payload.competency_id == self.attempt.competency_id
        assert lost.payload.progress == str(self.progress.current_progress)
        assert lost.payload.lost_at == NOW.astimezone(UTC).isoformat().replace(
            '+00:00', 'Z'
        )

    def test_should_not_announce_a_mastery_transition_that_did_not_happen(
        self,
    ) -> None:
        self.subject.execute(self.attempt.id, 'run-1')

        names = [
            call.args[0].name for call in self.repositories.events.add.call_args_list
        ]
        assert 'learning/competency-mastery-lost' not in names
        assert 'learning/competency-mastered' not in names

    def _as_diagnostic(self, diagnostic_run_id: str) -> None:
        self.attempt = ActivityAttempt.create(
            id=self.attempt.id,
            skill_experience_id=self.attempt.skill_experience_id,
            competency_id=self.attempt.competency_id,
            activity_id=self.attempt.activity_id,
            kind=ActivityAttemptKind.DIAGNOSTIC,
            answers=self.attempt.answers,
            submitted_at=self.attempt.submitted_at,
            submission_key=self.attempt.submission_key,
            grading_snapshot=self.attempt.grading_snapshot,
            diagnostic_run_id=diagnostic_run_id,
        )
        self.repositories.activity_attempts.find_by_id.return_value = self.attempt

    def test_should_ignore_a_diagnostic_attempt_outside_its_run(self) -> None:
        self._as_diagnostic('another-run')
        self.experience.status = SkillExperienceStatus.DIAGNOSING
        self.experience.diagnostic_run_id = 'the-run'

        self.subject.execute(self.attempt.id, 'run-1')

        self.repositories.activity_evaluations.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_ignore_a_diagnostic_attempt_once_diagnosing_ended(self) -> None:
        self._as_diagnostic('the-run')
        self.experience.status = SkillExperienceStatus.LEARNING
        self.experience.diagnostic_run_id = 'the-run'

        self.subject.execute(self.attempt.id, 'run-1')

        self.repositories.activity_evaluations.update.assert_not_called()
        self.repositories.events.add.assert_not_called()
