from datetime import UTC, datetime, timedelta
from dataclasses import replace
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
    ActivityDifficulty,
    ActivityEvaluationStatus,
    CompetencyProgressStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.structures import ConceptObservation
from shifu.learning.core.domain.structures.competency_completion_summary import (
    CompetencyCompletionSummary,
)
from shifu.learning.core.domain.structures.skill_completion_summary import (
    SkillCompletionSummary,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases.get_diagnostic_use_case import GetDiagnosticUseCase
from shifu.shared.core.domain.errors import ConflictError
from shifu.shared.core.domain.structures import (
    CurriculumActivitySnapshot,
    CurriculumCompetencySnapshot,
    CurriculumConceptSnapshot,
    CurriculumSkillSnapshot,
)
from shifu.shared.core.interfaces import ClockProvider, CurriculumContentProvider

NOW = datetime(2026, 9, 23, 12, tzinfo=UTC)
RUN_ID = 'diagnostic-run'
LEVELS = (ActivityDifficulty.EASY, ActivityDifficulty.MEDIUM, ActivityDifficulty.HARD)


def catalog() -> CurriculumSkillSnapshot:
    concept = CurriculumConceptSnapshot(
        id='concept',
        competency_id='competency',
        name='Conceito',
        position=1,
        prerequisite_ids=(),
        observation_criteria='Critério',
    )
    activities = tuple(
        CurriculumActivitySnapshot(
            id=f'diagnostic-{difficulty.value}',
            title='Diagnóstico',
            activity_type='diagnostic',
            difficulty=difficulty.value,
            position=index,
            concept_ids=('concept',),
            question_count_by_concept=(('concept', 1),),
            maximum_evidence_by_concept=(('concept', 1),),
            executable_concept_evidence=True,
        )
        for index, difficulty in enumerate(LEVELS, 1)
    )
    return CurriculumSkillSnapshot(
        id='skill',
        name='Skill',
        competencies=(
            CurriculumCompetencySnapshot(
                id='competency',
                skill_id='skill',
                name='Competência',
                position=1,
                items=(
                    CurriculumActivitySnapshot(
                        id='learning-hard',
                        title='Atividade de aprendizagem',
                        activity_type='learning',
                        difficulty=ActivityDifficulty.HARD.value,
                        position=1,
                        concept_ids=('concept',),
                        question_count_by_concept=(('concept', 1),),
                        executable_concept_evidence=True,
                    ),
                ),
                concepts=(concept,),
                diagnostic_activities=activities,
            ),
        ),
    )


class TestGetDiagnosticUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(LearningDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.provider = create_autospec(CurriculumContentProvider, instance=True)
        self.provider.get_skill_content.return_value = catalog()
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = NOW
        self.goal = GoalFaker.fake(id='goal', account_id='account')
        self.experience = SkillExperienceFaker.fake(
            id='experience',
            goal_id='goal',
            skill_id='skill',
            status=SkillExperienceStatus.DIAGNOSING,
        )
        self.experience.diagnostic_run_id = RUN_ID
        self.repositories.goals.find_by_id.return_value = self.goal
        self.repositories.skill_experiences.find_by_goal_id_and_skill_id.return_value = self.experience
        self.repositories.activity_attempts.find_many_by_skill_experience_id_and_diagnostic_run_id.return_value = []
        self.repositories.activity_evaluations.find_many_by_attempt_ids.return_value = []
        self.subject = GetDiagnosticUseCase(self.database, self.provider, self.clock)

    def test_should_require_new_entry_when_key_is_absent(self) -> None:
        overview = self.subject.execute('account', 'goal', 'skill')

        assert overview.run_state == 'requires_entry'
        assert overview.next_activity_id is None
        assert overview.ready_to_complete is False
        self.repositories.activity_attempts.find_many_by_skill_experience_id_and_diagnostic_run_id.assert_not_called()

    def test_should_return_first_curricular_item_for_the_active_run(self) -> None:
        overview = self.subject.execute('account', 'goal', 'skill', RUN_ID)

        assert overview.run_state == 'active'
        assert overview.next_competency_id == 'competency'
        assert overview.next_activity_id == 'diagnostic-easy'
        self.repositories.activity_attempts.find_many_by_skill_experience_id_and_diagnostic_run_id.assert_called_once_with(
            'experience', RUN_ID
        )

    def test_should_keep_a_pending_attempt_private_and_in_sequence(self) -> None:
        attempt = ActivityAttempt.create(
            id='attempt-easy',
            skill_experience_id='experience',
            competency_id='competency',
            activity_id='diagnostic-easy',
            kind=ActivityAttemptKind.DIAGNOSTIC,
            answers=(),
            submitted_at=NOW,
            diagnostic_run_id=RUN_ID,
        )
        evaluation = ActivityEvaluation.create(
            id='evaluation-easy',
            attempt_id=attempt.id,
            status=ActivityEvaluationStatus.PENDING,
            parts=(),
            started_at=NOW,
            run_id='evaluation-run',
        )
        self.repositories.activity_attempts.find_many_by_skill_experience_id_and_diagnostic_run_id.return_value = [
            attempt
        ]
        self.repositories.activity_evaluations.find_many_by_attempt_ids.return_value = [
            evaluation
        ]

        overview = self.subject.execute('account', 'goal', 'skill', RUN_ID)

        assert overview.run_state == 'active'
        assert overview.next_activity_id == 'diagnostic-easy'
        assert overview.pending_attempt_id == attempt.id
        assert overview.pending_attempt_status is ActivityEvaluationStatus.PENDING
        assert not hasattr(overview, 'score')

    def test_should_timeout_a_stale_pending_attempt_without_exposing_its_result(
        self,
    ) -> None:
        attempt = ActivityAttempt.create(
            id='attempt-easy',
            skill_experience_id='experience',
            competency_id='competency',
            activity_id='diagnostic-easy',
            kind=ActivityAttemptKind.DIAGNOSTIC,
            answers=(),
            submitted_at=NOW - timedelta(minutes=6),
            diagnostic_run_id=RUN_ID,
        )
        evaluation = ActivityEvaluation.create(
            id='evaluation-easy',
            attempt_id=attempt.id,
            status=ActivityEvaluationStatus.PENDING,
            parts=(),
            started_at=NOW - timedelta(minutes=6),
            run_id='evaluation-run',
        )
        self.repositories.activity_attempts.find_many_by_skill_experience_id_and_diagnostic_run_id.return_value = [
            attempt
        ]
        self.repositories.activity_evaluations.find_many_by_attempt_ids.return_value = [
            evaluation
        ]
        self.repositories.activity_evaluations.find_by_attempt_id_for_update.return_value = evaluation

        overview = self.subject.execute('account', 'goal', 'skill', RUN_ID)

        assert overview.pending_attempt_status is ActivityEvaluationStatus.FAILED
        assert evaluation.failure_code == 'evaluation_timeout'
        assert not hasattr(overview, 'score')
        self.repositories.activity_evaluations.update.assert_called_once_with(
            evaluation
        )

    def test_should_reject_a_replaced_run_without_reading_attempts(self) -> None:
        with pytest.raises(ConflictError):
            self.subject.execute('account', 'goal', 'skill', 'old-run')

        self.repositories.activity_attempts.find_many_by_skill_experience_id_and_diagnostic_run_id.assert_not_called()

    def test_should_signal_completion_without_exposing_scores(self) -> None:
        attempts = tuple(
            ActivityAttempt.create(
                id=f'attempt-{difficulty.value}',
                skill_experience_id='experience',
                competency_id='competency',
                activity_id=f'diagnostic-{difficulty.value}',
                kind=ActivityAttemptKind.DIAGNOSTIC,
                answers=(),
                submitted_at=NOW,
                diagnostic_run_id=RUN_ID,
            )
            for difficulty in LEVELS
        )
        evaluations = tuple(
            ActivityEvaluation.create(
                id=f'evaluation-{attempt.id}',
                attempt_id=attempt.id,
                status=ActivityEvaluationStatus.COMPLETED,
                parts=(),
                started_at=NOW,
                score=Decimal('90'),
                completed_at=NOW,
            )
            for attempt in attempts
        )
        self.repositories.activity_attempts.find_many_by_skill_experience_id_and_diagnostic_run_id.return_value = list(
            attempts
        )
        self.repositories.activity_evaluations.find_many_by_attempt_ids.return_value = (
            list(evaluations)
        )

        overview = self.subject.execute('account', 'goal', 'skill', RUN_ID)

        assert overview.run_state == 'ready_to_complete'
        assert overview.ready_to_complete is True
        assert overview.next_activity_id is None
        assert not hasattr(overview, 'score')

    def test_should_keep_existing_summary_private_while_diagnosing(self) -> None:
        attempt = ActivityAttempt.create(
            id='attempt-easy',
            skill_experience_id='experience',
            competency_id='competency',
            activity_id='diagnostic-easy',
            kind=ActivityAttemptKind.DIAGNOSTIC,
            answers=(),
            submitted_at=NOW,
            diagnostic_run_id=RUN_ID,
        )
        evaluation = ActivityEvaluation.create(
            id='evaluation-easy',
            attempt_id=attempt.id,
            status=ActivityEvaluationStatus.COMPLETED,
            parts=(),
            started_at=NOW,
            score=Decimal('100'),
            completed_at=NOW,
        )
        self.repositories.activity_attempts.find_many_by_skill_experience_id_and_diagnostic_run_id.return_value = [
            attempt
        ]
        self.repositories.activity_evaluations.find_many_by_attempt_ids.return_value = [
            evaluation
        ]

        overview = self.subject.execute('account', 'goal', 'skill', RUN_ID)

        assert overview.run_state == 'active'
        assert overview.next_activity_id == 'diagnostic-medium'
        assert not hasattr(overview, 'score')

    def test_settled_overview_reconstructs_only_the_initial_diagnostic_state(
        self,
    ) -> None:
        self.experience.status = SkillExperienceStatus.LEARNING
        self.experience.recommended_concept_id = 'later-learning-target'
        diagnostic_observations = (
            ConceptObservation(
                attempt_id='attempt-diagnostic-easy',
                activity_id='diagnostic-easy',
                concept_id='concept',
                difficulty=ActivityDifficulty.EASY,
                first_submitted_at=NOW,
                submitted_at=NOW,
                completed_at=NOW,
                question_scores=(Decimal('100'),),
                diagnostic=True,
            ),
            ConceptObservation(
                attempt_id='attempt-diagnostic-medium',
                activity_id='diagnostic-medium',
                concept_id='concept',
                difficulty=ActivityDifficulty.MEDIUM,
                first_submitted_at=NOW,
                submitted_at=NOW,
                completed_at=NOW,
                question_scores=(Decimal('0'),),
                diagnostic=True,
            ),
            ConceptObservation(
                attempt_id='attempt-diagnostic-hard',
                activity_id='diagnostic-hard',
                concept_id='concept',
                difficulty=ActivityDifficulty.HARD,
                first_submitted_at=NOW,
                submitted_at=NOW,
                completed_at=NOW,
                question_scores=(Decimal('0'),),
                diagnostic=True,
            ),
        )
        mutable_progress = CompetencyProgress(
            id='progress',
            skill_experience_id='experience',
            competency_id='competency',
            content_released=False,
            created_at=NOW,
            updated_at=NOW,
            initial_progress=Decimal('70'),
            current_progress=Decimal('99'),
            status=CompetencyProgressStatus.MASTERED,
            mastered_at=NOW,
            coverage_complete=True,
        )
        self.repositories.concept_observations.find_many_by_skill_experience_id.return_value = list(
            diagnostic_observations
        )
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
            mutable_progress
        ]

        first = self.subject.execute('account', 'goal', 'skill', RUN_ID)

        assert first.run_state == 'settled'
        assert first.initial_overall_result == Decimal('100') / Decimal('3')
        assert first.overall_coverage_complete is True
        assert first.focus_competency_id == 'competency'
        assert first.competencies[0].progress == Decimal('100') / Decimal('3')
        assert first.competencies[0].coverage_complete is True
        assert first.competencies[0].status is CompetencyProgressStatus.LEARNING
        assert first.competencies[0].is_focus is True
        assert first.competencies[0].content_released is True
        assert first.initial_recommendation is not None
        assert first.initial_recommendation.activity_id == 'learning-hard'
        assert first.initial_recommendation.target_concept_name == 'Conceito'
        assert first.initial_recommendation.difficulty is ActivityDifficulty.HARD
        assert first.initial_recommendation.reason == 'practice'
        assert first.initial_recommendation.gap is None

        mutable_progress.current_progress = Decimal('40')
        mutable_progress.status = CompetencyProgressStatus.LEARNING
        mutable_progress.mastered_at = None
        mutable_progress.coverage_complete = False
        mutable_progress.content_released = False
        self.experience.recommended_concept_id = 'another-learning-target'
        second = self.subject.execute('account', 'goal', 'skill', RUN_ID)

        assert second.competencies == first.competencies
        assert second.initial_overall_result == first.initial_overall_result
        assert second.overall_coverage_complete == first.overall_coverage_complete
        assert second.focus_competency_id == first.focus_competency_id
        assert second.initial_recommendation == first.initial_recommendation
        self.repositories.competency_progresses.find_many_by_skill_experience_id.assert_not_called()

    def test_settled_overview_prefers_the_persisted_completion_snapshot(self) -> None:
        self.experience.status = SkillExperienceStatus.COMPLETED
        self.experience.completion_summary = SkillCompletionSummary(
            competencies=(
                CompetencyCompletionSummary(
                    competency_id='competency',
                    initial_progress=Decimal('42'),
                    final_progress=Decimal('91'),
                    initial_coverage_complete=True,
                ),
            ),
            initial_progress=Decimal('42'),
            final_progress=Decimal('91'),
            started_at=NOW,
            completed_at=NOW,
            initial_coverage_complete=True,
        )
        self.repositories.concept_observations.find_many_by_skill_experience_id.return_value = []

        overview = self.subject.execute('account', 'goal', 'skill', RUN_ID)

        assert overview.initial_overall_result == Decimal('42')
        assert overview.overall_coverage_complete is True
        assert overview.competencies[0].progress == Decimal('42')
        assert overview.competencies[0].coverage_complete is True

    def test_settled_overview_preserves_gap_when_no_learning_fallback_exists(
        self,
    ) -> None:
        self.experience.status = SkillExperienceStatus.LEARNING
        skill_catalog = catalog()
        competency = skill_catalog.competencies[0]
        self.provider.get_skill_content.return_value = replace(
            skill_catalog,
            competencies=(replace(competency, items=()),),
        )
        self.repositories.concept_observations.find_many_by_skill_experience_id.return_value = [
            ConceptObservation(
                attempt_id=f'attempt-diagnostic-{difficulty.value}',
                activity_id=f'diagnostic-{difficulty.value}',
                concept_id='concept',
                difficulty=difficulty,
                first_submitted_at=NOW,
                submitted_at=NOW,
                completed_at=NOW,
                question_scores=(Decimal(score),),
                diagnostic=True,
            )
            for difficulty, score in zip(LEVELS, ('100', '0', '0'), strict=True)
        ]

        overview = self.subject.execute('account', 'goal', 'skill', RUN_ID)

        assert overview.run_state == 'settled'
        assert overview.initial_recommendation is None
        assert overview.initial_recommendation_gap == (
            'curriculum_or_assessment_unavailable'
        )
