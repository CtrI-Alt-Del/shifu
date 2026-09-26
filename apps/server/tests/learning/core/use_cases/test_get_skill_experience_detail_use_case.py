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
    ActivityRecommendationType,
    CompetencyAvailability,
    CompetencyProgressStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.errors import SkillExperienceDetailNotFoundError
from shifu.learning.core.domain.structures import (
    ActivityRecommendation,
    AvailableCompetencyDetail,
    CompetencyDetail,
    SkillExperienceDetail,
    SkillRecommendation,
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

    def execute(self, account_id: str = ACCOUNT_ID) -> SkillExperienceDetail:
        return self.subject.execute(account_id, GOAL_ID, SKILL_ID)

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

    def test_should_treat_a_competency_without_progress_as_blocked_at_zero(
        self,
    ) -> None:
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = []

        detail = self.execute()

        summary = detail.competencies[0]
        assert summary.progress == Decimal('0')
        assert summary.availability is CompetencyAvailability.UNAVAILABLE
        assert summary.status is CompetencyProgressStatus.LEARNING

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
