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
)
from shifu.learning.core.domain.errors import CompetencyDetailNotFoundError
from shifu.learning.core.domain.structures import (
    AvailableCompetencyDetail,
    CompetencyActivityDetail,
    UnavailableCompetencyDetail,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases import GetCompetencyDetailUseCase
from shifu.shared.core.domain.structures import (
    CurriculumActivitySnapshot,
    CurriculumCompetencySnapshot,
    CurriculumMaterialSnapshot,
    CurriculumSkillSnapshot,
)
from shifu.shared.core.interfaces import CurriculumContentProvider

ACCOUNT_ID = 'account-1'
GOAL_ID = 'goal-1'
SKILL_ID = 'skill-1'
COMPETENCY_ID = 'competency-1'
SECOND_COMPETENCY_ID = 'competency-2'
EXPERIENCE_ID = 'experience-1'


def at(minute: int) -> datetime:
    return datetime(2026, 1, 1, 12, minute, tzinfo=UTC)


def material(
    material_id: str,
    position: int,
) -> CurriculumMaterialSnapshot:
    return CurriculumMaterialSnapshot(
        id=material_id,
        title=f'Material {material_id}',
        material_type='theory',
        position=position,
    )


def activity(
    activity_id: str,
    position: int,
    difficulty: ActivityDifficulty,
) -> CurriculumActivitySnapshot:
    return CurriculumActivitySnapshot(
        id=activity_id,
        title=f'Atividade {activity_id}',
        activity_type='learning',
        difficulty=difficulty.value,
        position=position,
    )


def competency(
    competency_id: str,
    position: int,
    items: tuple[CurriculumMaterialSnapshot | CurriculumActivitySnapshot, ...],
) -> CurriculumCompetencySnapshot:
    return CurriculumCompetencySnapshot(
        id=competency_id,
        skill_id=SKILL_ID,
        name=f'Competência {competency_id}',
        position=position,
        items=items,
    )


def progress(
    competency_id: str,
    *,
    released: bool = True,
    current: Decimal | None = Decimal('35'),
    initial: Decimal | None = Decimal('20'),
    status: CompetencyProgressStatus | None = CompetencyProgressStatus.LEARNING,
) -> CompetencyProgress:
    return CompetencyProgress(
        id=f'progress-{competency_id}',
        skill_experience_id=EXPERIENCE_ID,
        competency_id=competency_id,
        content_released=released,
        created_at=at(0),
        updated_at=at(0),
        initial_progress=initial,
        current_progress=current,
        status=status,
        mastered_at=at(0) if status is CompetencyProgressStatus.MASTERED else None,
        hard_activity_score=(
            Decimal('90') if status is CompetencyProgressStatus.MASTERED else None
        ),
    )


def attempt(
    attempt_id: str,
    activity_id: str,
    submitted_at: datetime,
    *,
    competency_id: str = COMPETENCY_ID,
    kind: ActivityAttemptKind = ActivityAttemptKind.LEARNING,
) -> ActivityAttempt:
    return ActivityAttempt(
        id=attempt_id,
        skill_experience_id=EXPERIENCE_ID,
        competency_id=competency_id,
        activity_id=activity_id,
        kind=kind,
        answers=(),
        submitted_at=submitted_at,
    )


def evaluation(
    evaluation_id: str,
    attempt_id: str,
    score: Decimal,
    *,
    completed_at: datetime | None = None,
    status: ActivityEvaluationStatus = ActivityEvaluationStatus.COMPLETED,
) -> ActivityEvaluation:
    started_at = at(1)
    return ActivityEvaluation(
        id=evaluation_id,
        attempt_id=attempt_id,
        status=status,
        parts=(),
        started_at=started_at,
        score=score if status is ActivityEvaluationStatus.COMPLETED else None,
        failure_code='failed' if status is ActivityEvaluationStatus.FAILED else None,
        completed_at=(completed_at or started_at)
        if status is ActivityEvaluationStatus.COMPLETED
        else None,
    )


class TestGetCompetencyDetailUseCase:
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
        self.goal = GoalFaker.fake(id=GOAL_ID, account_id=ACCOUNT_ID)
        self.skill_experience = SkillExperienceFaker.fake(
            id=EXPERIENCE_ID,
            goal_id=GOAL_ID,
            skill_id=SKILL_ID,
        )
        self.repositories.goals.find_by_id.return_value = self.goal
        self.repositories.skill_experiences.find_by_goal_id_and_skill_id.return_value = self.skill_experience
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = []
        self.repositories.activity_attempts.find_many_by_skill_experience_id.return_value = []
        self.repositories.activity_evaluations.find_many_by_attempt_ids.return_value = []
        self.subject = GetCompetencyDetailUseCase(
            self.learning_database,
            self.curriculum_content_provider,
        )

    def test_should_reject_private_absence_before_requesting_curriculum(self) -> None:
        self.repositories.goals.find_by_id.return_value = None

        with pytest.raises(CompetencyDetailNotFoundError):
            self.subject.execute(ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID)

        self.curriculum_content_provider.get_skill_content.assert_not_called()
        self.repositories.skill_experiences.find_by_goal_id_and_skill_id.assert_not_called()
        self._assert_no_writes()

    def test_should_reject_mismatched_curriculum_hierarchy(self) -> None:
        self.curriculum_content_provider.get_skill_content.return_value = (
            CurriculumSkillSnapshot(id='another-skill', name='Outra', competencies=())
        )

        with pytest.raises(CompetencyDetailNotFoundError):
            self.subject.execute(ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID)

        self.repositories.competency_progresses.find_many_by_skill_experience_id.assert_not_called()
        self._assert_no_writes()

    def test_should_project_available_detail_in_official_order_with_latest_scores(
        self,
    ) -> None:
        current_competency = competency(
            COMPETENCY_ID,
            1,
            (
                activity('activity-2', 3, ActivityDifficulty.EASY),
                material('material-1', 1),
                activity('activity-1', 2, ActivityDifficulty.EASY),
            ),
        )
        self.curriculum_content_provider.get_skill_content.return_value = (
            CurriculumSkillSnapshot(
                id=SKILL_ID,
                name='Lógica de programação',
                competencies=(current_competency,),
            )
        )
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
            progress(COMPETENCY_ID, current=None, initial=Decimal('35'), status=None)
        ]
        old_attempt = attempt('attempt-1', 'activity-1', at(2))
        latest_attempt = attempt('attempt-2', 'activity-1', at(3))
        diagnostic_attempt = attempt(
            'attempt-3',
            'activity-2',
            at(4),
            kind=ActivityAttemptKind.DIAGNOSTIC,
        )
        self.repositories.activity_attempts.find_many_by_skill_experience_id.return_value = [
            old_attempt,
            latest_attempt,
            diagnostic_attempt,
        ]
        self.repositories.activity_evaluations.find_many_by_attempt_ids.return_value = [
            evaluation(
                'evaluation-1', old_attempt.id, Decimal('40'), completed_at=at(5)
            ),
            evaluation(
                'evaluation-2',
                latest_attempt.id,
                Decimal('80'),
                completed_at=at(6),
            ),
            evaluation(
                'evaluation-3',
                diagnostic_attempt.id,
                Decimal('100'),
                completed_at=at(7),
            ),
        ]

        result = self.subject.execute(ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID)

        assert isinstance(result, AvailableCompetencyDetail)
        assert result.availability is CompetencyAvailability.AVAILABLE
        assert result.progress == Decimal('35')
        assert result.status is CompetencyProgressStatus.LEARNING
        assert [item.id for item in result.items] == [
            'material-1',
            'activity-1',
            'activity-2',
        ]
        activities = [
            item for item in result.items if isinstance(item, CompetencyActivityDetail)
        ]
        assert [(item.id, item.latest_score) for item in activities] == [
            ('activity-1', Decimal('80')),
            ('activity-2', None),
        ]
        assert result.recommendation is not None
        assert result.recommendation.activity_id == 'activity-2'
        assert result.recommendation.type is ActivityRecommendationType.NEW_ACTIVITY
        self._assert_no_writes()

    def test_should_preserve_zero_current_progress_before_initial_progress(
        self,
    ) -> None:
        current_competency = competency(
            COMPETENCY_ID,
            1,
            (activity('activity-1', 1, ActivityDifficulty.EASY),),
        )
        self.curriculum_content_provider.get_skill_content.return_value = (
            CurriculumSkillSnapshot(
                id=SKILL_ID,
                name='Lógica de programação',
                competencies=(current_competency,),
            )
        )
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
            progress(
                COMPETENCY_ID,
                current=Decimal('0'),
                initial=Decimal('35'),
            )
        ]

        result = self.subject.execute(ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID)

        assert isinstance(result, AvailableCompetencyDetail)
        assert result.progress == Decimal('0')
        assert result.recommendation is not None
        assert result.recommendation.difficulty is ActivityDifficulty.EASY
        self._assert_no_writes()

    def test_should_derive_focus_returned_and_avoid_an_equal_score_repeat(self) -> None:
        current_competency = competency(
            COMPETENCY_ID,
            1,
            (
                activity('easy-1', 1, ActivityDifficulty.EASY),
                activity('easy-2', 2, ActivityDifficulty.EASY),
            ),
        )
        later_competency = competency(SECOND_COMPETENCY_ID, 2, ())
        self.curriculum_content_provider.get_skill_content.return_value = (
            CurriculumSkillSnapshot(
                id=SKILL_ID,
                name='Lógica',
                competencies=(current_competency, later_competency),
            )
        )
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
            progress(COMPETENCY_ID, current=Decimal('39')),
            progress(
                SECOND_COMPETENCY_ID,
                current=Decimal('90'),
                initial=Decimal('90'),
                status=CompetencyProgressStatus.MASTERED,
            ),
        ]
        first_attempt = attempt('attempt-1', 'easy-1', at(2))
        second_attempt = attempt('attempt-2', 'easy-2', at(3))
        self.repositories.activity_attempts.find_many_by_skill_experience_id.return_value = [
            first_attempt,
            second_attempt,
        ]
        self.repositories.activity_evaluations.find_many_by_attempt_ids.return_value = [
            evaluation(
                'evaluation-1', first_attempt.id, Decimal('20'), completed_at=at(4)
            ),
            evaluation(
                'evaluation-2', second_attempt.id, Decimal('20'), completed_at=at(5)
            ),
        ]

        result = self.subject.execute(ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID)

        assert isinstance(result, AvailableCompetencyDetail)
        assert result.is_focus is True
        assert result.focus_returned is True
        assert result.focus_competency_id == COMPETENCY_ID
        assert result.recommendation is not None
        assert result.recommendation.activity_id == 'easy-1'
        assert result.recommendation.type is ActivityRecommendationType.REINFORCEMENT
        self._assert_no_writes()

    @pytest.mark.parametrize(
        ('progress_value', 'expected_difficulty'),
        [
            (Decimal('40'), ActivityDifficulty.MEDIUM),
            (Decimal('70'), ActivityDifficulty.HARD),
        ],
    )
    def test_should_map_threshold_edges_to_target_difficulty(
        self,
        progress_value: Decimal,
        expected_difficulty: ActivityDifficulty,
    ) -> None:
        current_competency = competency(
            COMPETENCY_ID,
            1,
            (activity('target', 1, expected_difficulty),),
        )
        self.curriculum_content_provider.get_skill_content.return_value = (
            CurriculumSkillSnapshot(
                id=SKILL_ID,
                name='Lógica',
                competencies=(current_competency,),
            )
        )
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
            progress(COMPETENCY_ID, current=progress_value)
        ]

        result = self.subject.execute(ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID)

        assert isinstance(result, AvailableCompetencyDetail)
        assert result.recommendation is not None
        assert result.recommendation.difficulty is expected_difficulty
        self._assert_no_writes()

    def test_should_return_unavailable_without_progress_or_content_reads(self) -> None:
        current_competency = competency(
            COMPETENCY_ID,
            1,
            (activity('activity-1', 1, ActivityDifficulty.EASY),),
        )
        self.curriculum_content_provider.get_skill_content.return_value = (
            CurriculumSkillSnapshot(
                id=SKILL_ID,
                name='Lógica',
                competencies=(current_competency,),
            )
        )

        result = self.subject.execute(ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID)

        assert isinstance(result, UnavailableCompetencyDetail)
        assert result.availability is CompetencyAvailability.UNAVAILABLE
        assert result.focus_competency_id == COMPETENCY_ID
        assert not hasattr(result, 'progress')
        self.repositories.activity_attempts.find_many_by_skill_experience_id.assert_not_called()
        self.repositories.activity_evaluations.find_many_by_attempt_ids.assert_not_called()
        self._assert_no_writes()

    def test_should_return_released_non_focus_without_recommendation(self) -> None:
        first_competency = competency(
            COMPETENCY_ID,
            1,
            (activity('first-activity', 1, ActivityDifficulty.EASY),),
        )
        focus_competency = competency(
            SECOND_COMPETENCY_ID,
            2,
            (activity('focus-activity', 1, ActivityDifficulty.EASY),),
        )
        self.curriculum_content_provider.get_skill_content.return_value = (
            CurriculumSkillSnapshot(
                id=SKILL_ID,
                name='Lógica',
                competencies=(first_competency, focus_competency),
            )
        )
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
            progress(
                COMPETENCY_ID,
                current=Decimal('90'),
                status=CompetencyProgressStatus.MASTERED,
            ),
            progress(SECOND_COMPETENCY_ID),
        ]

        result = self.subject.execute(ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID)

        assert isinstance(result, AvailableCompetencyDetail)
        assert result.is_focus is False
        assert result.recommendation is None
        assert result.focus_competency_id == SECOND_COMPETENCY_ID
        self._assert_no_writes()

    def test_should_omit_focus_and_recommendation_when_every_competency_is_mastered(
        self,
    ) -> None:
        current_competency = competency(
            COMPETENCY_ID,
            1,
            (activity('activity-1', 1, ActivityDifficulty.HARD),),
        )
        self.curriculum_content_provider.get_skill_content.return_value = (
            CurriculumSkillSnapshot(
                id=SKILL_ID,
                name='Lógica',
                competencies=(current_competency,),
            )
        )
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
            progress(
                COMPETENCY_ID,
                current=Decimal('90'),
                initial=Decimal('90'),
                status=CompetencyProgressStatus.MASTERED,
            )
        ]

        result = self.subject.execute(ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID)

        assert isinstance(result, AvailableCompetencyDetail)
        assert result.is_focus is False
        assert result.focus_competency_id is None
        assert result.recommendation is None
        self._assert_no_writes()

    def _assert_no_writes(self) -> None:
        for repository in (
            self.repositories.goals,
            self.repositories.skill_experiences,
            self.repositories.competency_progresses,
            self.repositories.activity_attempts,
            self.repositories.activity_evaluations,
            self.repositories.events,
        ):
            for method_name in ('add', 'add_many', 'update', 'remove', 'remove_all'):
                method = getattr(repository, method_name, None)
                if method is not None:
                    method.assert_not_called()
