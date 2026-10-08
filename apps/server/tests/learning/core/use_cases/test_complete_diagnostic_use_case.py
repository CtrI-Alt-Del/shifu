from datetime import UTC, datetime
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
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases.complete_diagnostic_use_case import (
    CompleteDiagnosticUseCase,
)
from shifu.shared.core.domain.errors import ConflictError, NotFoundError
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
    competency = CurriculumCompetencySnapshot(
        id='competency',
        skill_id='skill',
        name='Competência',
        position=1,
        items=(),
        concepts=(concept,),
        diagnostic_activities=activities,
    )
    return CurriculumSkillSnapshot(id='skill', name='Skill', competencies=(competency,))


class TestCompleteDiagnosticUseCase:
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
        self.progress = CompetencyProgress(
            id='progress',
            skill_experience_id='experience',
            competency_id='competency',
            content_released=True,
            created_at=NOW,
            updated_at=NOW,
            status=CompetencyProgressStatus.LEARNING,
        )
        self.attempts = tuple(
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
        self.evaluations = tuple(
            ActivityEvaluation.create(
                id=f'evaluation-{attempt.id}',
                attempt_id=attempt.id,
                status=ActivityEvaluationStatus.COMPLETED,
                parts=(),
                started_at=NOW,
                score=Decimal('90'),
                completed_at=NOW,
                run_id=f'evaluation-run-{attempt.id}',
            )
            for attempt in self.attempts
        )
        self.observations = tuple(
            ConceptObservation(
                attempt_id=attempt.id,
                activity_id=attempt.activity_id,
                concept_id='concept',
                difficulty=difficulty,
                first_submitted_at=NOW,
                submitted_at=NOW,
                completed_at=NOW,
                question_scores=(Decimal('90'),),
                diagnostic=True,
            )
            for attempt, difficulty in zip(self.attempts, LEVELS, strict=True)
        )
        self.repositories.goals.find_by_id.return_value = self.goal
        self.repositories.skill_experiences.find_by_goal_id_and_skill_id.return_value = self.experience
        self.repositories.skill_experiences.find_by_id_for_update.return_value = (
            self.experience
        )
        self.repositories.activity_attempts.find_many_by_skill_experience_id_and_diagnostic_run_id.return_value = list(
            self.attempts
        )
        self.repositories.activity_evaluations.find_many_by_attempt_ids.return_value = (
            list(self.evaluations)
        )
        self.repositories.concept_observations.find_many_by_skill_experience_id.return_value = list(
            self.observations
        )
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
            self.progress
        ]
        self.subject = CompleteDiagnosticUseCase(
            self.database, self.provider, self.clock
        )

    def execute(self, run_id: str = RUN_ID) -> None:
        self.subject.execute('account', 'goal', 'skill', run_id)

    def test_should_confirm_all_diagnostic_effects_once_and_complete_directly(
        self,
    ) -> None:
        self.execute()

        assert self.experience.status is SkillExperienceStatus.COMPLETED
        assert self.experience.diagnostic_run_id == RUN_ID
        assert self.experience.completion_summary is not None
        assert self.experience.completion_summary.initial_progress == Decimal('90')
        assert self.experience.completion_summary.final_progress == Decimal('90')
        assert self.progress.initial_progress == Decimal('90')
        assert self.progress.current_progress == Decimal('90')
        assert self.progress.coverage_complete is True
        assert all(item.effect_applied_at == NOW for item in self.evaluations)
        event_names = [
            call.args[0].name for call in self.repositories.events.add.call_args_list
        ]

        assert event_names == [
            'learning/skill-completed',
            'learning/diagnostic-completed',
        ]

        self.execute()

        assert self.repositories.events.add.call_count == 2

    def test_should_reject_incomplete_run_without_progress_or_events(self) -> None:
        self.repositories.activity_evaluations.find_many_by_attempt_ids.return_value = (
            list(self.evaluations[:-1])
        )

        with pytest.raises(ConflictError):
            self.execute()

        self.repositories.competency_progresses.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_reject_stale_run_after_authorizing_experience(self) -> None:
        with pytest.raises(ConflictError):
            self.execute('stale-run')

        self.repositories.activity_attempts.find_many_by_skill_experience_id_and_diagnostic_run_id.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_hide_experience_from_another_account(self) -> None:
        self.repositories.goals.find_by_id.return_value = None

        with pytest.raises(NotFoundError):
            self.execute()

        self.repositories.skill_experiences.find_by_id_for_update.assert_not_called()
