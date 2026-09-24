from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import create_autospec

import pytest

from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.learning.core.domain.entities import CompetencyProgress
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.domain.errors import GoalNotFoundError
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases import GetGoalDetailUseCase
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures import CurriculumSkillOverview
from shifu.shared.core.interfaces import CurriculumContentProvider


ACCOUNT_ID = 'account-1'
GOAL_ID = 'goal-1'


class TestGetGoalDetailUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(
            LearningDatabaseRepositories,
            instance=True,
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.curriculum_content_provider = create_autospec(
            CurriculumContentProvider,
            instance=True,
        )
        self.goal = GoalFaker.fake(id=GOAL_ID, account_id=ACCOUNT_ID)
        self.repositories.goals.find_by_id.return_value = self.goal
        self.repositories.skill_experiences.find_many_by_goal_id.return_value = []
        self.subject = GetGoalDetailUseCase(
            self.database,
            self.curriculum_content_provider,
        )

    def test_should_return_owned_empty_goal_without_requesting_curriculum(self) -> None:
        detail = self.subject.execute(ACCOUNT_ID, GOAL_ID)

        assert detail.goal_id == GOAL_ID
        assert detail.title == self.goal.title
        assert detail.description == self.goal.description
        assert detail.skills == ()
        assert detail.relations == ()
        self.curriculum_content_provider.get_skill_overviews.assert_not_called()
        self._assert_no_writes()

    def test_should_keep_other_account_goal_private_before_requesting_curriculum(
        self,
    ) -> None:
        self.goal.account_id = 'other-account'

        with pytest.raises(GoalNotFoundError):
            self.subject.execute(ACCOUNT_ID, GOAL_ID)

        self.repositories.skill_experiences.find_many_by_goal_id.assert_not_called()
        self.curriculum_content_provider.get_skill_overviews.assert_not_called()
        self._assert_no_writes()

    def test_should_project_skills_relations_and_learning_progress(self) -> None:
        skill_a = SkillExperienceFaker.fake(
            id='experience-a',
            goal_id=GOAL_ID,
            skill_id='skill-a',
            status=SkillExperienceStatus.LEARNING,
            inclusion_reason='Fundamento necessário.',
        )
        skill_b = SkillExperienceFaker.fake(
            id='experience-b',
            goal_id=GOAL_ID,
            skill_id='skill-b',
            status=SkillExperienceStatus.DIAGNOSING,
        )
        skill_c = SkillExperienceFaker.fake(
            id='experience-c',
            goal_id=GOAL_ID,
            skill_id='skill-c',
            status=SkillExperienceStatus.COMPLETED,
        )
        self.repositories.skill_experiences.find_many_by_goal_id.return_value = [
            skill_c,
            skill_a,
            skill_b,
        ]
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
            _progress('progress-a1', 'experience-a', 'competency-a1', Decimal('30')),
            _progress('progress-a2', 'experience-a', 'competency-a2', Decimal('90')),
        ]
        self.curriculum_content_provider.get_skill_overviews.return_value = (
            CurriculumSkillOverview(
                skill_id='skill-c',
                name='Zulu',
                competency_ids=('competency-c',),
                foundation_skill_ids=('skill-a', 'outside-skill'),
            ),
            CurriculumSkillOverview(
                skill_id='skill-a',
                name='Álgebra',
                competency_ids=('competency-a1', 'competency-a2'),
                foundation_skill_ids=(),
            ),
            CurriculumSkillOverview(
                skill_id='skill-b',
                name='Beta',
                competency_ids=('competency-b',),
                foundation_skill_ids=('skill-a',),
            ),
        )

        detail = self.subject.execute(ACCOUNT_ID, GOAL_ID)

        assert [skill.skill_id for skill in detail.skills] == [
            'skill-b',
            'skill-c',
            'skill-a',
        ]
        learning_skill = next(
            skill for skill in detail.skills if skill.skill_id == 'skill-a'
        )
        assert learning_skill.progress == Decimal('60')
        assert learning_skill.inclusion_reason == 'Fundamento necessário.'
        assert all(
            skill.progress is None
            for skill in detail.skills
            if skill.skill_id != 'skill-a'
        )
        assert [
            (relation.foundation_skill_id, relation.skill_id)
            for relation in detail.relations
        ] == [('skill-a', 'skill-b'), ('skill-a', 'skill-c')]
        self.curriculum_content_provider.get_skill_overviews.assert_called_once_with(
            ('skill-c', 'skill-a', 'skill-b')
        )
        assert (
            self.repositories.competency_progresses.find_many_by_skill_experience_id.call_count
            == 1
        )
        self._assert_no_writes()

    def test_should_reject_missing_curriculum_metadata_without_partial_projection(
        self,
    ) -> None:
        experience = SkillExperienceFaker.fake(
            goal_id=GOAL_ID,
            skill_id='skill-a',
        )
        self.repositories.skill_experiences.find_many_by_goal_id.return_value = [
            experience
        ]
        self.curriculum_content_provider.get_skill_overviews.return_value = ()

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute(ACCOUNT_ID, GOAL_ID)

        self._assert_no_writes()

    def test_should_reject_learning_progress_when_any_official_competency_is_missing(
        self,
    ) -> None:
        experience = SkillExperienceFaker.fake(
            id='experience-a',
            goal_id=GOAL_ID,
            skill_id='skill-a',
            status=SkillExperienceStatus.LEARNING,
        )
        self.repositories.skill_experiences.find_many_by_goal_id.return_value = [
            experience
        ]
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
            _progress('progress-a1', 'experience-a', 'competency-a1', Decimal('30'))
        ]
        self.curriculum_content_provider.get_skill_overviews.return_value = (
            CurriculumSkillOverview(
                skill_id='skill-a',
                name='Skill A',
                competency_ids=('competency-a1', 'competency-a2'),
                foundation_skill_ids=(),
            ),
        )

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute(ACCOUNT_ID, GOAL_ID)

        self._assert_no_writes()

    def test_should_reject_experience_from_another_goal(self) -> None:
        self.repositories.skill_experiences.find_many_by_goal_id.return_value = [
            SkillExperienceFaker.fake(goal_id='another-goal', skill_id='skill-a')
        ]

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute(ACCOUNT_ID, GOAL_ID)

        self.curriculum_content_provider.get_skill_overviews.assert_not_called()
        self._assert_no_writes()

    def _assert_no_writes(self) -> None:
        self.repositories.goals.add.assert_not_called()
        self.repositories.goals.update.assert_not_called()
        self.repositories.skill_experiences.add.assert_not_called()
        self.repositories.skill_experiences.update.assert_not_called()
        self.repositories.competency_progresses.add.assert_not_called()
        self.repositories.competency_progresses.update.assert_not_called()
        self.repositories.events.add.assert_not_called()


def _progress(
    progress_id: str,
    skill_experience_id: str,
    competency_id: str,
    current_progress: Decimal,
) -> CompetencyProgress:
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    return CompetencyProgress(
        id=progress_id,
        skill_experience_id=skill_experience_id,
        competency_id=competency_id,
        content_released=True,
        created_at=created_at,
        updated_at=created_at,
        initial_progress=current_progress,
        current_progress=current_progress,
    )
