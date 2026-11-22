import logging
from dataclasses import fields, replace
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import create_autospec

import pytest

from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.learning.core.domain.entities import (
    ActivityAttempt,
    ActivityEvaluation,
    CompetencyProgress,
    Goal,
    SkillExperience,
)
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityDifficulty,
    ActivityEvaluationStatus,
    ActivityRecommendationType,
    CompetencyAvailability,
    CompetencyProgressStatus,
    SkillExperienceStatus,
    StartingPointCoverage,
)
from shifu.learning.core.domain.errors import SkillExperienceDetailNotFoundError
from shifu.learning.core.domain.structures import (
    AdaptiveConceptState,
    ActivityRecommendation,
    AvailableCompetencyDetail,
    CompetencyCompletionOverview,
    CompetencyCompletionSummary,
    CompetencyDetail,
    ConceptCompletionSummary,
    ConceptObservation,
    SkillCompletionOverview,
    SkillCompletionSummary,
    SkillExperienceDetail,
    SkillRecommendation,
    SkillReviewOverview,
    UnavailableCompetencyDetail,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases import (
    GetCompetencyDetailUseCase,
    GetSkillExperienceDetailUseCase,
)
from shifu.shared.core.domain.structures import (
    CurriculumActivitySnapshot,
    CurriculumCompetencySnapshot,
    CurriculumConceptSnapshot,
    CurriculumSkillSnapshot,
)
from shifu.shared.core.interfaces import CurriculumContentProvider

ACCOUNT_ID = 'account-1'
GOAL_ID = 'goal-1'
SKILL_ID = 'skill-1'
EXPERIENCE_ID = 'experience-1'
FIRST_COMPETENCY_ID = 'competency-1'
SECOND_COMPETENCY_ID = 'competency-2'
THIRD_COMPETENCY_ID = 'competency-3'
ACTIVITY_ID = 'activity-1'
ATTEMPT_ID = 'attempt-1'
EVALUATION_ID = 'evaluation-1'


def at(minute: int) -> datetime:
    return datetime(2026, 1, 1, 12, minute, tzinfo=UTC)


def competency(
    competency_id: str,
    position: int,
) -> CurriculumCompetencySnapshot:
    return CurriculumCompetencySnapshot(
        id=competency_id,
        skill_id=SKILL_ID,
        name=f'Competência {position}',
        position=position,
        items=(
            CurriculumActivitySnapshot(
                id=f'{competency_id}-activity',
                title='Atividade',
                activity_type='learning',
                difficulty=ActivityDifficulty.EASY.value,
                position=1,
            ),
        ),
    )


def skill_content(
    competencies: tuple[CurriculumCompetencySnapshot, ...],
) -> CurriculumSkillSnapshot:
    return CurriculumSkillSnapshot(
        id=SKILL_ID,
        name='Lógica de programação',
        competencies=competencies,
    )


def progress(
    competency_id: str,
    *,
    released: bool = True,
    current: Decimal | None = Decimal('35'),
    status: CompetencyProgressStatus | None = CompetencyProgressStatus.LEARNING,
) -> CompetencyProgress:
    return CompetencyProgress(
        id=f'progress-{competency_id}',
        skill_experience_id=EXPERIENCE_ID,
        competency_id=competency_id,
        content_released=released,
        created_at=at(0),
        updated_at=at(0),
        initial_progress=Decimal('20'),
        current_progress=current,
        status=status,
        mastered_at=at(0) if status is CompetencyProgressStatus.MASTERED else None,
        hard_activity_score=(
            Decimal('90') if status is CompetencyProgressStatus.MASTERED else None
        ),
    )


def mastered(competency_id: str) -> CompetencyProgress:
    return progress(
        competency_id,
        current=Decimal('92'),
        status=CompetencyProgressStatus.MASTERED,
    )


def attempt() -> ActivityAttempt:
    return ActivityAttempt(
        id=ATTEMPT_ID,
        skill_experience_id=EXPERIENCE_ID,
        competency_id=FIRST_COMPETENCY_ID,
        activity_id=ACTIVITY_ID,
        kind=ActivityAttemptKind.LEARNING,
        answers=(),
        submitted_at=at(1),
    )


def held_evaluation(status: ActivityEvaluationStatus) -> ActivityEvaluation:
    return ActivityEvaluation(
        id=EVALUATION_ID,
        attempt_id=ATTEMPT_ID,
        status=status,
        parts=(),
        started_at=at(1),
        failure_code='evaluator_unavailable'
        if status is ActivityEvaluationStatus.FAILED
        else None,
    )


def available_competency(
    competency_id: str,
    recommendation: ActivityRecommendation | None,
) -> AvailableCompetencyDetail:
    return AvailableCompetencyDetail(
        goal_id=GOAL_ID,
        skill_id=SKILL_ID,
        skill_name='Lógica de programação',
        competency_id=competency_id,
        competency_name='Competência 1',
        availability=CompetencyAvailability.AVAILABLE,
        progress=Decimal('35'),
        status=CompetencyProgressStatus.LEARNING,
        is_focus=recommendation is not None,
        focus_returned=False,
        focus_competency_id=competency_id,
        focus_competency_name='Competência 1',
        items=(),
        recommendation=recommendation,
    )


def recommendation(competency_id: str) -> ActivityRecommendation:
    return ActivityRecommendation(
        competency_id=competency_id,
        activity_id=f'{competency_id}-activity',
        difficulty=ActivityDifficulty.EASY,
        type=ActivityRecommendationType.NEW_ACTIVITY,
    )


def expected_recommendation(competency_id: str, position: int) -> SkillRecommendation:
    return SkillRecommendation(
        competency_id=competency_id,
        competency_name=f'Competência {position}',
        activity_id=f'{competency_id}-activity',
        activity_title='Atividade',
        difficulty=ActivityDifficulty.EASY,
        type=ActivityRecommendationType.NEW_ACTIVITY,
        reason=ActivityRecommendationType.NEW_ACTIVITY.value,
    )


def focus_detail(
    _account_id: str,
    _goal_id: str,
    _skill_id: str,
    competency_id: str,
) -> CompetencyDetail:
    return available_competency(competency_id, recommendation(competency_id))


def unavailable_focus_detail(
    _account_id: str,
    _goal_id: str,
    _skill_id: str,
    competency_id: str,
) -> CompetencyDetail:
    return UnavailableCompetencyDetail(
        goal_id=GOAL_ID,
        skill_id=SKILL_ID,
        skill_name='Lógica de programação',
        competency_id=competency_id,
        competency_name='Competência 1',
        availability=CompetencyAvailability.UNAVAILABLE,
        focus_competency_id=competency_id,
        focus_competency_name='Competência 1',
    )


CONCEPT_IDS = ('concept-1', 'concept-2', 'concept-3')
ALL_DIFFICULTIES = (
    ActivityDifficulty.EASY,
    ActivityDifficulty.MEDIUM,
    ActivityDifficulty.HARD,
)
STARTED_AT = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)
COMPLETED_AT = datetime(2026, 9, 13, 15, 0, tzinfo=UTC)


def competency_with_concepts(
    competency_id: str,
    position: int,
    concept_ids: tuple[str, ...],
) -> CurriculumCompetencySnapshot:
    return replace(
        competency(competency_id, position),
        concepts=tuple(
            CurriculumConceptSnapshot(
                id=concept_id,
                competency_id=competency_id,
                name=f'Conceito {concept_id}',
                position=index,
                prerequisite_ids=(),
                observation_criteria='Critério',
            )
            for index, concept_id in enumerate(concept_ids, start=1)
        ),
    )


def stored_concept(
    concept_id: str,
    difficulties: tuple[ActivityDifficulty, ...] = ALL_DIFFICULTIES,
) -> ConceptCompletionSummary:
    return ConceptCompletionSummary(
        concept_id=concept_id,
        initial_progress=Decimal('50'),
        final_progress=Decimal('90'),
        initial_observed_difficulties=difficulties,
        final_observed_difficulties=ALL_DIFFICULTIES,
    )


def stored_competency(
    competency_id: str,
    initial: Decimal | None,
    final: Decimal,
    concepts: tuple[ConceptCompletionSummary, ...] = (),
) -> CompetencyCompletionSummary:
    return CompetencyCompletionSummary(
        competency_id=competency_id,
        initial_progress=initial,
        final_progress=final,
        concepts=concepts,
    )


def stored_summary(
    competencies: tuple[CompetencyCompletionSummary, ...],
    *,
    initial: Decimal | None = Decimal('50'),
    final: Decimal = Decimal('85'),
    started_at: datetime = STARTED_AT,
    completed_at: datetime = COMPLETED_AT,
) -> SkillCompletionSummary:
    return SkillCompletionSummary(
        competencies=competencies,
        initial_progress=initial,
        final_progress=final,
        started_at=started_at,
        completed_at=completed_at,
    )


def mastered_progress(
    competency_id: str,
    mastered_at: datetime | None,
) -> CompetencyProgress:
    return CompetencyProgress(
        id=f'progress-{competency_id}',
        skill_experience_id=EXPERIENCE_ID,
        competency_id=competency_id,
        content_released=True,
        created_at=at(0),
        updated_at=at(0),
        initial_progress=Decimal('20'),
        current_progress=Decimal('90'),
        status=CompetencyProgressStatus.LEARNING,
        mastered_at=mastered_at,
    )


def kind_attempt(
    attempt_id: str,
    kind: ActivityAttemptKind,
    activity_id: str,
) -> ActivityAttempt:
    return ActivityAttempt(
        id=attempt_id,
        skill_experience_id=EXPERIENCE_ID,
        competency_id=FIRST_COMPETENCY_ID,
        activity_id=activity_id,
        kind=kind,
        answers=(),
        submitted_at=at(1),
    )


def finished_evaluation(
    attempt_id: str,
    score: Decimal,
    completed_at: datetime,
) -> ActivityEvaluation:
    return ActivityEvaluation(
        id=f'evaluation-{attempt_id}',
        attempt_id=attempt_id,
        status=ActivityEvaluationStatus.COMPLETED,
        parts=(),
        started_at=at(1),
        score=score,
        completed_at=completed_at,
    )


def diagnostic_observation(
    concept_id: str,
    difficulty: ActivityDifficulty,
    *,
    score: Decimal | None = Decimal('80'),
    diagnostic: bool = True,
) -> ConceptObservation:
    return ConceptObservation(
        attempt_id=f'observation-{concept_id}-{difficulty.value}',
        activity_id=f'activity-{concept_id}-{difficulty.value}',
        concept_id=concept_id,
        difficulty=difficulty,
        first_submitted_at=at(1),
        submitted_at=at(1),
        completed_at=at(2),
        question_scores=(score,),
        diagnostic=diagnostic,
    )


def overview_competency(
    competency_id: str,
    position: int,
    *,
    initial: Decimal | None,
    coverage: StartingPointCoverage,
    final: Decimal,
    mastered_on: date,
) -> CompetencyCompletionOverview:
    return CompetencyCompletionOverview(
        competency_id=competency_id,
        competency_name=f'Competência {position}',
        position=position,
        initial_progress=initial,
        initial_coverage=coverage,
        final_progress=final,
        mastered_on=mastered_on,
    )


class TestGetSkillExperienceDetailUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.learning_database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(
            LearningDatabaseRepositories,
            instance=True,
        )
        self.learning_database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.curriculum_content_provider = create_autospec(
            CurriculumContentProvider,
            instance=True,
        )
        self.competency_detail_use_case = create_autospec(
            GetCompetencyDetailUseCase,
            instance=True,
        )
        self.goal = GoalFaker.fake(id=GOAL_ID, account_id=ACCOUNT_ID)
        self.skill_experience = SkillExperienceFaker.fake(
            id=EXPERIENCE_ID,
            goal_id=GOAL_ID,
            skill_id=SKILL_ID,
            status=SkillExperienceStatus.LEARNING,
        )
        self.repositories.goals.find_by_id.return_value = self.goal
        self.repositories.skill_experiences.find_by_goal_id_and_skill_id.return_value = self.skill_experience
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = []
        self.repositories.activity_evaluations.find_unresolved_by_skill_experience_id.return_value = None
        self.curriculum_content_provider.get_skill_content.return_value = skill_content(
            (competency(FIRST_COMPETENCY_ID, 1),)
        )
        self.competency_detail_use_case.execute.side_effect = focus_detail
        self.subject = GetSkillExperienceDetailUseCase(
            self.learning_database,
            self.curriculum_content_provider,
            self.competency_detail_use_case,
        )

    def execute(
        self,
        account_id: str = ACCOUNT_ID,
        time_zone: str | None = None,
    ) -> SkillExperienceDetail:
        return self.subject.execute(account_id, GOAL_ID, SKILL_ID, time_zone)

    def test_should_start_displayed_progress_from_diagnostic_evidence_and_update_after_practice(
        self,
    ) -> None:
        concepts = tuple(
            CurriculumConceptSnapshot(
                id=f'concept-{index}',
                competency_id=FIRST_COMPETENCY_ID,
                name=f'Conceito {index}',
                position=index,
                prerequisite_ids=(),
                observation_criteria='Critério',
            )
            for index in (1, 2)
        )
        first_competency = competency(FIRST_COMPETENCY_ID, 1)
        self.curriculum_content_provider.get_skill_content.return_value = skill_content(
            (replace(first_competency, concepts=concepts),)
        )
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
            progress(FIRST_COMPETENCY_ID, current=Decimal('100'))
        ]

        def state(concept_id: str, value: Decimal | None) -> AdaptiveConceptState:
            return AdaptiveConceptState(
                concept_id=concept_id,
                initial_progress=Decimal('100') if concept_id == 'concept-1' else None,
                progress=value,
                observed_difficulties=frozenset(),
                distinct_activity_ids=frozenset(),
                hard_confirmation=False,
                evidence_verification=False,
                inconclusive_activity_ids=(),
                current_contributions=(),
            )

        self.repositories.concept_states.find_many_by_skill_experience_id.return_value = [
            state('concept-1', Decimal('100')),
            state('concept-2', None),
        ]
        baseline = self.execute()

        assert baseline.overall_result == Decimal('50')
        assert baseline.competencies[0].progress == Decimal('50')

        self.repositories.concept_states.find_many_by_skill_experience_id.return_value = [
            state('concept-1', Decimal('100')),
            state('concept-2', Decimal('50')),
        ]
        after_practice = self.execute()

        assert after_practice.overall_result == Decimal('75')
        assert after_practice.competencies[0].progress == Decimal('75')

    def test_should_reject_a_goal_of_another_account_before_reading_curriculum(
        self,
    ) -> None:
        self.goal = GoalFaker.fake(id=GOAL_ID, account_id='other-account')
        self.repositories.goals.find_by_id.return_value = self.goal

        with pytest.raises(SkillExperienceDetailNotFoundError):
            self.execute()

        self.curriculum_content_provider.get_skill_content.assert_not_called()

    def test_should_reject_an_absent_goal(self) -> None:
        self.repositories.goals.find_by_id.return_value = None

        with pytest.raises(SkillExperienceDetailNotFoundError):
            self.execute()

    def test_should_reject_a_skill_outside_the_goal_experience(self) -> None:
        self.repositories.skill_experiences.find_by_goal_id_and_skill_id.return_value = None

        with pytest.raises(SkillExperienceDetailNotFoundError):
            self.execute()

    def test_should_reject_a_skill_without_curricular_content(self) -> None:
        self.curriculum_content_provider.get_skill_content.return_value = None

        with pytest.raises(SkillExperienceDetailNotFoundError):
            self.execute()

    def test_should_describe_the_experience_of_the_owner(self) -> None:
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
            progress(FIRST_COMPETENCY_ID)
        ]

        detail = self.execute()

        assert detail.skill_name == 'Lógica de programação'
        assert detail.skill_status is SkillExperienceStatus.LEARNING
        assert detail.goal_id == GOAL_ID
        assert detail.skill_id == SKILL_ID

    def test_should_list_every_competency_in_curricular_order(self) -> None:
        self.curriculum_content_provider.get_skill_content.return_value = skill_content(
            (
                competency(THIRD_COMPETENCY_ID, 3),
                competency(FIRST_COMPETENCY_ID, 1),
                competency(SECOND_COMPETENCY_ID, 2),
            )
        )
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
            mastered(FIRST_COMPETENCY_ID),
            progress(SECOND_COMPETENCY_ID),
        ]

        detail = self.execute()

        assert [item.position for item in detail.competencies] == [1, 2, 3]
        assert [item.competency_id for item in detail.competencies] == [
            FIRST_COMPETENCY_ID,
            SECOND_COMPETENCY_ID,
            THIRD_COMPETENCY_ID,
        ]

    def test_should_expose_progress_status_and_availability_of_each_competency(
        self,
    ) -> None:
        self.curriculum_content_provider.get_skill_content.return_value = skill_content(
            (
                competency(FIRST_COMPETENCY_ID, 1),
                competency(SECOND_COMPETENCY_ID, 2),
            )
        )
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
            mastered(FIRST_COMPETENCY_ID),
            progress(SECOND_COMPETENCY_ID, released=False),
        ]

        detail = self.execute()

        first, second = detail.competencies

        assert first.progress == Decimal('92')
        assert first.status is CompetencyProgressStatus.MASTERED
        assert first.availability is CompetencyAvailability.AVAILABLE
        assert second.progress == Decimal('35')
        assert second.status is CompetencyProgressStatus.LEARNING
        assert second.availability is CompetencyAvailability.UNAVAILABLE

    def test_should_leave_progress_unknown_when_a_competency_has_no_progress(
        self,
    ) -> None:
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = []

        detail = self.execute()

        summary = detail.competencies[0]

        assert summary.progress is None
        assert summary.availability is CompetencyAvailability.UNAVAILABLE
        assert summary.status is None

    def test_should_average_every_competency_including_the_blocked_ones(self) -> None:
        self.curriculum_content_provider.get_skill_content.return_value = skill_content(
            (
                competency(FIRST_COMPETENCY_ID, 1),
                competency(SECOND_COMPETENCY_ID, 2),
            )
        )
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
            mastered(FIRST_COMPETENCY_ID),
            progress(SECOND_COMPETENCY_ID, released=False, current=Decimal('40')),
        ]

        detail = self.execute()

        assert detail.overall_result == Decimal('66')

    def test_should_focus_the_first_competency_that_is_not_mastered(self) -> None:
        self.curriculum_content_provider.get_skill_content.return_value = skill_content(
            (
                competency(FIRST_COMPETENCY_ID, 1),
                competency(SECOND_COMPETENCY_ID, 2),
            )
        )
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
            mastered(FIRST_COMPETENCY_ID),
            progress(SECOND_COMPETENCY_ID),
        ]

        detail = self.execute()

        assert detail.focus_competency_id == SECOND_COMPETENCY_ID
        assert detail.competencies[0].is_focus is False
        assert detail.competencies[1].is_focus is True

    def test_should_leave_no_focus_when_every_competency_is_mastered(self) -> None:
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
            mastered(FIRST_COMPETENCY_ID)
        ]

        detail = self.execute()

        assert detail.focus_competency_id is None
        assert detail.focus_competency_name is None
        assert detail.recommendation is None
        self.competency_detail_use_case.execute.assert_not_called()

    def test_should_delegate_the_recommendation_to_the_focus_competency(self) -> None:
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
            progress(FIRST_COMPETENCY_ID)
        ]

        detail = self.execute()

        assert detail.recommendation == expected_recommendation(FIRST_COMPETENCY_ID, 1)
        self.competency_detail_use_case.execute.assert_called_once_with(
            ACCOUNT_ID,
            GOAL_ID,
            SKILL_ID,
            FIRST_COMPETENCY_ID,
        )

    def test_should_omit_the_recommendation_when_the_focus_is_not_released(
        self,
    ) -> None:
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
            progress(FIRST_COMPETENCY_ID, released=False)
        ]
        self.competency_detail_use_case.execute.side_effect = unavailable_focus_detail

        detail = self.execute()

        assert detail.recommendation is None

    def test_should_report_a_pending_evaluation_and_suspend_the_recommendation(
        self,
    ) -> None:
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
            progress(FIRST_COMPETENCY_ID)
        ]
        self.repositories.activity_evaluations.find_unresolved_by_skill_experience_id.return_value = held_evaluation(
            ActivityEvaluationStatus.PENDING
        )
        self.repositories.activity_attempts.find_by_id.return_value = attempt()

        detail = self.execute()

        assert detail.evaluation is not None
        assert detail.evaluation.status is ActivityEvaluationStatus.PENDING
        assert detail.evaluation.activity_id == ACTIVITY_ID
        assert detail.evaluation.competency_id == FIRST_COMPETENCY_ID
        assert detail.recommendation is None
        self.competency_detail_use_case.execute.assert_not_called()

    def test_should_report_a_failed_evaluation_without_hiding_the_competencies(
        self,
    ) -> None:
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
            progress(FIRST_COMPETENCY_ID)
        ]
        self.repositories.activity_evaluations.find_unresolved_by_skill_experience_id.return_value = held_evaluation(
            ActivityEvaluationStatus.FAILED
        )
        self.repositories.activity_attempts.find_by_id.return_value = attempt()

        detail = self.execute()

        assert detail.evaluation is not None
        assert detail.evaluation.status is ActivityEvaluationStatus.FAILED
        assert detail.evaluation.evaluation_id == EVALUATION_ID
        assert len(detail.competencies) == 1
        assert detail.competencies[0].availability is CompetencyAvailability.AVAILABLE

    def test_should_ignore_an_evaluation_whose_attempt_is_from_another_experience(
        self,
    ) -> None:
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
            progress(FIRST_COMPETENCY_ID)
        ]
        self.repositories.activity_evaluations.find_unresolved_by_skill_experience_id.return_value = held_evaluation(
            ActivityEvaluationStatus.FAILED
        )
        self.repositories.activity_attempts.find_by_id.return_value = ActivityAttempt(
            id=ATTEMPT_ID,
            skill_experience_id='other-experience',
            competency_id=FIRST_COMPETENCY_ID,
            activity_id=ACTIVITY_ID,
            kind=ActivityAttemptKind.LEARNING,
            answers=(),
            submitted_at=at(1),
        )

        detail = self.execute()

        assert detail.evaluation is None

    def complete_experience(
        self,
        summary: SkillCompletionSummary,
        competencies: tuple[CurriculumCompetencySnapshot, ...],
        *,
        progresses: list[CompetencyProgress] | None = None,
        attempts: list[ActivityAttempt] | None = None,
        evaluations: list[ActivityEvaluation] | None = None,
        observations: list[ConceptObservation] | None = None,
    ) -> None:
        self.skill_experience = SkillExperienceFaker.fake(
            id=EXPERIENCE_ID,
            goal_id=GOAL_ID,
            skill_id=SKILL_ID,
            status=SkillExperienceStatus.COMPLETED,
            started_at=summary.started_at,
            completed_at=summary.completed_at,
            completion_summary=summary,
        )
        self.repositories.skill_experiences.find_by_goal_id_and_skill_id.return_value = self.skill_experience
        self.curriculum_content_provider.get_skill_content.return_value = skill_content(
            competencies
        )
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = (
            progresses or []
        )
        self.repositories.activity_attempts.find_many_by_skill_experience_id.return_value = (
            attempts or []
        )
        self.repositories.activity_evaluations.find_many_by_attempt_ids.return_value = (
            evaluations or []
        )
        self.repositories.concept_observations.find_many_by_skill_experience_id.return_value = (
            observations or []
        )

    def assert_no_repository_writes(self) -> None:
        for field in fields(LearningDatabaseRepositories):
            repository = getattr(self.repositories, field.name)
            for call in repository.mock_calls:
                assert call[0].startswith('find'), (field.name, call[0])

    def two_competency_summary(
        self,
        *,
        first_concepts: tuple[ConceptCompletionSummary, ...],
        second_concepts: tuple[ConceptCompletionSummary, ...] = (),
        first_initial: Decimal | None = Decimal('40'),
        second_initial: Decimal | None = Decimal('60'),
        initial: Decimal | None = Decimal('50'),
        started_at: datetime = STARTED_AT,
        completed_at: datetime = COMPLETED_AT,
    ) -> SkillCompletionSummary:
        return stored_summary(
            (
                stored_competency(
                    FIRST_COMPETENCY_ID,
                    first_initial,
                    Decimal('90'),
                    first_concepts,
                ),
                stored_competency(
                    SECOND_COMPETENCY_ID,
                    second_initial,
                    Decimal('80'),
                    second_concepts,
                ),
            ),
            initial=initial,
            started_at=started_at,
            completed_at=completed_at,
        )

    def two_competencies(self) -> tuple[CurriculumCompetencySnapshot, ...]:
        return (
            competency_with_concepts(
                FIRST_COMPETENCY_ID, 1, ('concept-1', 'concept-2')
            ),
            competency_with_concepts(SECOND_COMPETENCY_ID, 2, ('concept-3',)),
        )

    @pytest.mark.parametrize(
        'status',
        [
            SkillExperienceStatus.NOT_STARTED,
            SkillExperienceStatus.DIAGNOSING,
            SkillExperienceStatus.LEARNING,
        ],
    )
    def test_should_leave_completion_empty_and_read_no_extra_source_before_completion(
        self,
        status: SkillExperienceStatus,
    ) -> None:
        self.skill_experience = SkillExperienceFaker.fake(
            id=EXPERIENCE_ID,
            goal_id=GOAL_ID,
            skill_id=SKILL_ID,
            status=status,
        )
        self.repositories.skill_experiences.find_by_goal_id_and_skill_id.return_value = self.skill_experience

        detail = self.execute()

        assert detail.skill_status is status
        assert detail.completion is None
        self.repositories.activity_attempts.find_many_by_skill_experience_id.assert_not_called()
        self.repositories.activity_evaluations.find_many_by_attempt_ids.assert_not_called()
        self.repositories.concept_observations.find_many_by_skill_experience_id.assert_not_called()

    def test_should_build_the_overview_of_a_completed_skill_with_complete_coverage(
        self,
    ) -> None:
        self.complete_experience(
            self.two_competency_summary(
                first_concepts=(
                    stored_concept('concept-1'),
                    stored_concept('concept-2'),
                ),
                second_concepts=(stored_concept('concept-3'),),
            ),
            self.two_competencies(),
            progresses=[
                mastered_progress(
                    FIRST_COMPETENCY_ID, datetime(2026, 9, 5, 1, 0, tzinfo=UTC)
                ),
                mastered_progress(
                    SECOND_COMPETENCY_ID, datetime(2026, 9, 13, 15, 0, tzinfo=UTC)
                ),
            ],
            attempts=[
                kind_attempt('a-1', ActivityAttemptKind.DIAGNOSTIC, 'diagnostic-1'),
                kind_attempt('a-2', ActivityAttemptKind.DIAGNOSTIC, 'diagnostic-2'),
                kind_attempt('a-3', ActivityAttemptKind.LEARNING, 'learning-1'),
                kind_attempt('a-4', ActivityAttemptKind.LEARNING, 'learning-1'),
                kind_attempt('a-5', ActivityAttemptKind.LEARNING, 'learning-2'),
                kind_attempt('a-6', ActivityAttemptKind.REVIEW, 'learning-1'),
            ],
            evaluations=[finished_evaluation('a-6', Decimal('70'), at(30))],
        )

        detail = self.execute(time_zone='America/Sao_Paulo')

        assert detail.skill_status is SkillExperienceStatus.COMPLETED
        assert detail.completion == SkillCompletionOverview(
            started_on=date(2026, 9, 2),
            completed_on=date(2026, 9, 13),
            duration_days=11,
            completed_by_diagnosis=False,
            learning_activity_count=2,
            learning_attempt_count=3,
            initial_result=Decimal('50'),
            initial_result_coverage=StartingPointCoverage.COMPLETE,
            final_result=Decimal('85'),
            competencies=(
                overview_competency(
                    FIRST_COMPETENCY_ID,
                    1,
                    initial=Decimal('40'),
                    coverage=StartingPointCoverage.COMPLETE,
                    final=Decimal('90'),
                    mastered_on=date(2026, 9, 4),
                ),
                overview_competency(
                    SECOND_COMPETENCY_ID,
                    2,
                    initial=Decimal('60'),
                    coverage=StartingPointCoverage.COMPLETE,
                    final=Decimal('80'),
                    mastered_on=date(2026, 9, 13),
                ),
            ),
            review=SkillReviewOverview(attempt_count=1, latest_score=Decimal('70')),
        )
        self.repositories.activity_evaluations.find_many_by_attempt_ids.assert_called_once_with(
            ('a-6',)
        )
        self.assert_no_repository_writes()

    def test_should_label_partial_and_unknown_starting_points_and_average_the_known_ones(
        self,
    ) -> None:
        competencies = (
            competency_with_concepts(FIRST_COMPETENCY_ID, 1, ('concept-1',)),
            competency_with_concepts(SECOND_COMPETENCY_ID, 2, ('concept-2',)),
            competency_with_concepts(THIRD_COMPETENCY_ID, 3, ('concept-3',)),
        )
        summary = stored_summary(
            (
                stored_competency(
                    FIRST_COMPETENCY_ID,
                    Decimal('40'),
                    Decimal('90'),
                    (
                        stored_concept(
                            'concept-1',
                            (ActivityDifficulty.EASY, ActivityDifficulty.MEDIUM),
                        ),
                    ),
                ),
                stored_competency(SECOND_COMPETENCY_ID, None, Decimal('86')),
                stored_competency(
                    THIRD_COMPETENCY_ID,
                    Decimal('80'),
                    Decimal('95'),
                    (stored_concept('concept-3'),),
                ),
            ),
            initial=None,
            final=Decimal('90'),
        )
        self.complete_experience(summary, competencies)

        completion = self.execute().completion

        assert completion is not None
        assert [
            (item.competency_id, item.initial_progress, item.initial_coverage)
            for item in completion.competencies
        ] == [
            (FIRST_COMPETENCY_ID, Decimal('40'), StartingPointCoverage.PARTIAL),
            (SECOND_COMPETENCY_ID, None, StartingPointCoverage.UNKNOWN),
            (THIRD_COMPETENCY_ID, Decimal('80'), StartingPointCoverage.COMPLETE),
        ]
        assert completion.initial_result == Decimal('60')
        assert completion.initial_result_coverage is StartingPointCoverage.PARTIAL
        assert completion.final_result == Decimal('90')

    def test_should_leave_the_overall_start_unknown_when_no_competency_has_a_number(
        self,
    ) -> None:
        self.complete_experience(
            self.two_competency_summary(
                first_concepts=(),
                first_initial=None,
                second_initial=None,
                initial=None,
            ),
            self.two_competencies(),
        )

        completion = self.execute().completion

        assert completion is not None
        assert completion.initial_result is None
        assert completion.initial_result_coverage is StartingPointCoverage.UNKNOWN
        assert [item.initial_coverage for item in completion.competencies] == [
            StartingPointCoverage.UNKNOWN,
            StartingPointCoverage.UNKNOWN,
        ]
        assert [item.initial_progress for item in completion.competencies] == [
            None,
            None,
        ]

    def test_should_derive_coverage_from_diagnostic_observations_for_an_older_summary(
        self,
    ) -> None:
        full = [
            diagnostic_observation(concept_id, difficulty)
            for concept_id in ('concept-1', 'concept-2')
            for difficulty in ALL_DIFFICULTIES
        ]
        missing_hard = [
            diagnostic_observation('concept-3', ActivityDifficulty.EASY),
            diagnostic_observation('concept-3', ActivityDifficulty.MEDIUM),
            diagnostic_observation('concept-3', ActivityDifficulty.HARD, score=None),
        ]
        self.complete_experience(
            self.two_competency_summary(first_concepts=()),
            self.two_competencies(),
            observations=[*full, *missing_hard],
        )

        completion = self.execute().completion

        assert completion is not None
        assert [item.initial_coverage for item in completion.competencies] == [
            StartingPointCoverage.COMPLETE,
            StartingPointCoverage.PARTIAL,
        ]
        assert completion.initial_result_coverage is StartingPointCoverage.PARTIAL
        self.repositories.concept_observations.find_many_by_skill_experience_id.assert_called_once_with(
            EXPERIENCE_ID
        )

    def test_should_ignore_non_diagnostic_observations_when_deriving_coverage(
        self,
    ) -> None:
        learning = [
            diagnostic_observation('concept-3', difficulty, diagnostic=False)
            for difficulty in ALL_DIFFICULTIES
        ]
        self.complete_experience(
            self.two_competency_summary(first_concepts=()),
            self.two_competencies(),
            observations=learning,
        )

        completion = self.execute().completion

        assert completion is not None
        assert completion.competencies[1].initial_coverage is (
            StartingPointCoverage.PARTIAL
        )

    def test_should_prefer_stored_concept_data_over_diagnostic_observations(
        self,
    ) -> None:
        observations = [
            diagnostic_observation('concept-3', difficulty)
            for difficulty in ALL_DIFFICULTIES
        ]
        self.complete_experience(
            self.two_competency_summary(
                first_concepts=(),
                second_concepts=(
                    stored_concept('concept-3', (ActivityDifficulty.EASY,)),
                ),
            ),
            self.two_competencies(),
            observations=observations,
        )

        completion = self.execute().completion

        assert completion is not None
        assert completion.competencies[1].initial_coverage is (
            StartingPointCoverage.PARTIAL
        )

    def test_should_describe_a_skill_completed_by_the_diagnosis(self) -> None:
        self.complete_experience(
            self.two_competency_summary(
                first_concepts=(
                    stored_concept('concept-1'),
                    stored_concept('concept-2'),
                ),
                second_concepts=(stored_concept('concept-3'),),
                completed_at=datetime(2026, 9, 2, 13, 0, tzinfo=UTC),
            ),
            self.two_competencies(),
            progresses=[
                mastered_progress(
                    FIRST_COMPETENCY_ID, datetime(2026, 9, 2, 12, 30, tzinfo=UTC)
                ),
            ],
            attempts=[
                kind_attempt('a-1', ActivityAttemptKind.DIAGNOSTIC, 'diagnostic-1'),
            ],
        )

        completion = self.execute().completion

        assert completion == SkillCompletionOverview(
            started_on=date(2026, 9, 2),
            completed_on=date(2026, 9, 2),
            duration_days=0,
            completed_by_diagnosis=True,
            learning_activity_count=None,
            learning_attempt_count=None,
            initial_result=Decimal('50'),
            initial_result_coverage=StartingPointCoverage.COMPLETE,
            final_result=Decimal('85'),
            competencies=(
                overview_competency(
                    FIRST_COMPETENCY_ID,
                    1,
                    initial=Decimal('40'),
                    coverage=StartingPointCoverage.COMPLETE,
                    final=Decimal('90'),
                    mastered_on=date(2026, 9, 2),
                ),
                overview_competency(
                    SECOND_COMPETENCY_ID,
                    2,
                    initial=Decimal('60'),
                    coverage=StartingPointCoverage.COMPLETE,
                    final=Decimal('80'),
                    mastered_on=date(2026, 9, 2),
                ),
            ),
            review=SkillReviewOverview(attempt_count=0, latest_score=None),
        )
        self.repositories.activity_evaluations.find_many_by_attempt_ids.assert_not_called()

    def test_should_count_distinct_learning_activities_and_learning_attempts_only(
        self,
    ) -> None:
        self.complete_experience(
            self.two_competency_summary(first_concepts=()),
            self.two_competencies(),
            attempts=[
                kind_attempt('a-1', ActivityAttemptKind.DIAGNOSTIC, 'shared'),
                kind_attempt('a-2', ActivityAttemptKind.LEARNING, 'shared'),
                kind_attempt('a-3', ActivityAttemptKind.LEARNING, 'shared'),
                kind_attempt('a-4', ActivityAttemptKind.LEARNING, 'other'),
                kind_attempt('a-5', ActivityAttemptKind.REVIEW, 'shared'),
                kind_attempt('a-6', ActivityAttemptKind.REVIEW, 'third'),
            ],
        )

        completion = self.execute().completion

        assert completion is not None
        assert completion.completed_by_diagnosis is False
        assert completion.learning_activity_count == 2
        assert completion.learning_attempt_count == 3
        assert completion.review == SkillReviewOverview(
            attempt_count=2, latest_score=None
        )

    @pytest.mark.parametrize(
        ('started_at', 'completed_at', 'duration_days'),
        [
            (
                datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
                datetime(2026, 9, 2, 18, 0, tzinfo=UTC),
                0,
            ),
            (
                datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
                datetime(2026, 9, 3, 12, 0, tzinfo=UTC),
                1,
            ),
            (
                datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
                datetime(2026, 9, 13, 12, 0, tzinfo=UTC),
                11,
            ),
        ],
    )
    def test_should_count_the_duration_in_calendar_days(
        self,
        started_at: datetime,
        completed_at: datetime,
        duration_days: int,
    ) -> None:
        self.complete_experience(
            self.two_competency_summary(
                first_concepts=(),
                started_at=started_at,
                completed_at=completed_at,
            ),
            self.two_competencies(),
        )

        completion = self.execute(time_zone='UTC').completion

        assert completion is not None
        assert completion.duration_days == duration_days
        assert completion.started_on == started_at.date()
        assert completion.completed_on == completed_at.date()

    def test_should_follow_the_account_time_zone_when_it_shifts_the_days(self) -> None:
        self.complete_experience(
            self.two_competency_summary(
                first_concepts=(),
                started_at=datetime(2026, 9, 2, 23, 30, tzinfo=UTC),
                completed_at=datetime(2026, 9, 13, 2, 0, tzinfo=UTC),
            ),
            self.two_competencies(),
            progresses=[
                mastered_progress(
                    FIRST_COMPETENCY_ID, datetime(2026, 9, 10, 1, 0, tzinfo=UTC)
                ),
            ],
            attempts=[kind_attempt('a-1', ActivityAttemptKind.LEARNING, 'learning')],
        )

        local = self.execute(time_zone='America/Sao_Paulo').completion
        utc = self.execute(time_zone='UTC').completion

        assert local is not None
        assert utc is not None
        assert (local.started_on, local.completed_on, local.duration_days) == (
            date(2026, 9, 2),
            date(2026, 9, 12),
            10,
        )
        assert local.competencies[0].mastered_on == date(2026, 9, 9)
        assert (utc.started_on, utc.completed_on, utc.duration_days) == (
            date(2026, 9, 2),
            date(2026, 9, 13),
            11,
        )
        assert utc.competencies[0].mastered_on == date(2026, 9, 10)

    @pytest.mark.parametrize('time_zone', [None, '', 'Not/A_Zone', 'America/Nowhere'])
    def test_should_fall_back_to_utc_without_a_valid_time_zone(
        self,
        time_zone: str | None,
    ) -> None:
        self.complete_experience(
            self.two_competency_summary(
                first_concepts=(),
                started_at=datetime(2026, 9, 2, 23, 30, tzinfo=UTC),
                completed_at=datetime(2026, 9, 13, 2, 0, tzinfo=UTC),
            ),
            self.two_competencies(),
        )

        completion = self.execute(time_zone=time_zone).completion

        assert completion is not None
        assert (completion.started_on, completion.completed_on) == (
            date(2026, 9, 2),
            date(2026, 9, 13),
        )
        assert completion.duration_days == 11

    def test_should_use_the_completion_day_when_the_mastery_date_is_missing(
        self,
    ) -> None:
        self.complete_experience(
            self.two_competency_summary(first_concepts=()),
            self.two_competencies(),
            progresses=[mastered_progress(FIRST_COMPETENCY_ID, None)],
            attempts=[kind_attempt('a-1', ActivityAttemptKind.LEARNING, 'learning')],
        )

        completion = self.execute().completion

        assert completion is not None
        assert [item.mastered_on for item in completion.competencies] == [
            date(2026, 9, 13),
            date(2026, 9, 13),
        ]

    def test_should_leave_out_and_log_a_stored_competency_missing_from_the_curriculum(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        self.complete_experience(
            self.two_competency_summary(first_concepts=()),
            (competency_with_concepts(SECOND_COMPETENCY_ID, 2, ('concept-3',)),),
        )

        with caplog.at_level(logging.WARNING):
            completion = self.execute().completion

        assert completion is not None
        assert [item.competency_id for item in completion.competencies] == [
            SECOND_COMPETENCY_ID
        ]
        warnings = [
            record for record in caplog.records if record.levelno == logging.WARNING
        ]
        assert len(warnings) == 1
        assert warnings[0].args == (EXPERIENCE_ID, FIRST_COMPETENCY_ID)
        assert warnings[0].getMessage() == (
            'skill_completion_competency_missing '
            f'skill_experience_id={EXPERIENCE_ID} competency_id={FIRST_COMPETENCY_ID}'
        )

    def test_should_order_competencies_by_their_current_curriculum_position(
        self,
    ) -> None:
        self.complete_experience(
            self.two_competency_summary(first_concepts=()),
            (
                competency_with_concepts(FIRST_COMPETENCY_ID, 2, ('concept-1',)),
                competency_with_concepts(SECOND_COMPETENCY_ID, 1, ('concept-3',)),
            ),
        )

        completion = self.execute().completion

        assert completion is not None
        assert [
            (item.competency_id, item.position) for item in completion.competencies
        ] == [
            (SECOND_COMPETENCY_ID, 1),
            (FIRST_COMPETENCY_ID, 2),
        ]

    def test_should_report_no_review_attempts_without_a_score(self) -> None:
        self.complete_experience(
            self.two_competency_summary(first_concepts=()),
            self.two_competencies(),
            attempts=[kind_attempt('a-1', ActivityAttemptKind.LEARNING, 'learning')],
        )

        completion = self.execute().completion

        assert completion is not None
        assert completion.review == SkillReviewOverview(
            attempt_count=0, latest_score=None
        )
        self.repositories.activity_evaluations.find_many_by_attempt_ids.assert_not_called()

    def test_should_score_the_review_with_the_latest_finished_evaluation_and_count_a_pending_one(
        self,
    ) -> None:
        pending = ActivityEvaluation(
            id='evaluation-r3',
            attempt_id='r-3',
            status=ActivityEvaluationStatus.PENDING,
            parts=(),
            started_at=at(50),
        )
        self.complete_experience(
            self.two_competency_summary(first_concepts=()),
            self.two_competencies(),
            attempts=[
                kind_attempt('a-1', ActivityAttemptKind.LEARNING, 'learning'),
                kind_attempt('r-1', ActivityAttemptKind.REVIEW, 'learning'),
                kind_attempt('r-2', ActivityAttemptKind.REVIEW, 'learning'),
                kind_attempt('r-3', ActivityAttemptKind.REVIEW, 'learning'),
            ],
            evaluations=[
                finished_evaluation('r-1', Decimal('40'), at(10)),
                finished_evaluation('r-2', Decimal('85'), at(20)),
                pending,
                finished_evaluation('a-1', Decimal('99'), at(55)),
            ],
        )

        completion = self.execute().completion

        assert completion is not None
        assert completion.review == SkillReviewOverview(
            attempt_count=3, latest_score=Decimal('85')
        )
        self.repositories.activity_evaluations.find_many_by_attempt_ids.assert_called_once_with(
            ('r-1', 'r-2', 'r-3')
        )

    def test_should_keep_a_review_with_only_a_pending_evaluation_without_score(
        self,
    ) -> None:
        pending = ActivityEvaluation(
            id='evaluation-r1',
            attempt_id='r-1',
            status=ActivityEvaluationStatus.PENDING,
            parts=(),
            started_at=at(5),
        )
        self.complete_experience(
            self.two_competency_summary(first_concepts=()),
            self.two_competencies(),
            attempts=[kind_attempt('r-1', ActivityAttemptKind.REVIEW, 'learning')],
            evaluations=[pending],
        )

        completion = self.execute().completion

        assert completion is not None
        assert completion.review == SkillReviewOverview(
            attempt_count=1, latest_score=None
        )

    def test_should_keep_the_other_experience_of_the_same_skill_without_completion(
        self,
    ) -> None:
        other_goal_id = 'goal-2'
        other_experience = SkillExperienceFaker.fake(
            id='experience-2',
            goal_id=other_goal_id,
            skill_id=SKILL_ID,
            status=SkillExperienceStatus.LEARNING,
        )
        self.complete_experience(
            self.two_competency_summary(first_concepts=()),
            self.two_competencies(),
        )
        completed_experience = self.skill_experience

        def find_goal(goal_id: str) -> Goal:
            return GoalFaker.fake(id=goal_id, account_id=ACCOUNT_ID)

        def find_experience(goal_id: str, _skill_id: str) -> SkillExperience:
            return completed_experience if goal_id == GOAL_ID else other_experience

        self.repositories.goals.find_by_id.side_effect = find_goal
        self.repositories.skill_experiences.find_by_goal_id_and_skill_id.side_effect = (
            find_experience
        )

        completed = self.subject.execute(ACCOUNT_ID, GOAL_ID, SKILL_ID)
        other = self.subject.execute(ACCOUNT_ID, other_goal_id, SKILL_ID)

        assert completed.skill_status is SkillExperienceStatus.COMPLETED
        assert completed.completion is not None
        assert other.skill_status is SkillExperienceStatus.LEARNING
        assert other.completion is None

    def test_should_fail_unexpectedly_when_a_completed_skill_has_no_stored_summary(
        self,
    ) -> None:
        self.complete_experience(
            self.two_competency_summary(first_concepts=()),
            self.two_competencies(),
        )
        self.skill_experience.completion_summary = None

        with pytest.raises(RuntimeError):
            self.execute()

        self.assert_no_repository_writes()
