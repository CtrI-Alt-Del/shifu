from unittest.mock import create_autospec

import pytest

from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.domain.structures import SkillExperienceReference
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases import ListSkillExperiencesOfSkillUseCase

ACCOUNT_ID = 'account-1'
SKILL_ID = 'skill-1'


class TestListSkillExperiencesOfSkillUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(LearningDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.subject = ListSkillExperiencesOfSkillUseCase(self.database)

    def test_should_return_an_empty_list_without_querying_experiences_when_the_account_has_no_goals(
        self,
    ) -> None:
        self.repositories.goals.find_many_by_account_id.return_value = []

        result = self.subject.execute(ACCOUNT_ID, SKILL_ID)

        assert result == []
        self.repositories.goals.find_many_by_account_id.assert_called_once_with(
            ACCOUNT_ID
        )
        self.repositories.skill_experiences.find_many_by_goal_ids_and_skill_id.assert_not_called()

    def test_should_return_an_empty_list_when_no_goal_contains_the_skill(
        self,
    ) -> None:
        goals = [
            GoalFaker.fake(id='goal-1', account_id=ACCOUNT_ID, title='Backend'),
            GoalFaker.fake(id='goal-2', account_id=ACCOUNT_ID, title='Dados'),
        ]
        self.repositories.goals.find_many_by_account_id.return_value = goals
        self.repositories.skill_experiences.find_many_by_goal_ids_and_skill_id.return_value = []

        result = self.subject.execute(ACCOUNT_ID, SKILL_ID)

        assert result == []
        self.repositories.skill_experiences.find_many_by_goal_ids_and_skill_id.assert_called_once_with(
            ['goal-1', 'goal-2'], SKILL_ID
        )

    def test_should_map_experiences_of_two_goals_with_their_status_ordered_by_goal_title(
        self,
    ) -> None:
        goals = [
            GoalFaker.fake(id='goal-a', account_id=ACCOUNT_ID, title='Dados'),
            GoalFaker.fake(id='goal-b', account_id=ACCOUNT_ID, title='Backend'),
            GoalFaker.fake(
                id='goal-c', account_id=ACCOUNT_ID, title='Sem a Habilidade'
            ),
        ]
        in_data = SkillExperienceFaker.fake(
            id='experience-a',
            goal_id='goal-a',
            skill_id=SKILL_ID,
            status=SkillExperienceStatus.COMPLETED,
        )
        in_backend = SkillExperienceFaker.fake(
            id='experience-b',
            goal_id='goal-b',
            skill_id=SKILL_ID,
            status=SkillExperienceStatus.LEARNING,
        )
        self.repositories.goals.find_many_by_account_id.return_value = goals
        self.repositories.skill_experiences.find_many_by_goal_ids_and_skill_id.return_value = [
            in_data,
            in_backend,
        ]

        result = self.subject.execute(ACCOUNT_ID, SKILL_ID)

        assert result == [
            SkillExperienceReference(
                goal_id='goal-b',
                goal_title='Backend',
                skill_experience_id='experience-b',
                skill_id=SKILL_ID,
                status=SkillExperienceStatus.LEARNING,
            ),
            SkillExperienceReference(
                goal_id='goal-a',
                goal_title='Dados',
                skill_experience_id='experience-a',
                skill_id=SKILL_ID,
                status=SkillExperienceStatus.COMPLETED,
            ),
        ]
        self.repositories.skill_experiences.find_many_by_goal_ids_and_skill_id.assert_called_once_with(
            ['goal-a', 'goal-b', 'goal-c'], SKILL_ID
        )

    def test_should_order_experiences_by_goal_id_when_goal_titles_are_equal(
        self,
    ) -> None:
        goals = [
            GoalFaker.fake(id='goal-2', account_id=ACCOUNT_ID, title='Carreira'),
            GoalFaker.fake(id='goal-1', account_id=ACCOUNT_ID, title='Carreira'),
        ]
        self.repositories.goals.find_many_by_account_id.return_value = goals
        self.repositories.skill_experiences.find_many_by_goal_ids_and_skill_id.return_value = [
            SkillExperienceFaker.fake(id='experience-2', goal_id='goal-2'),
            SkillExperienceFaker.fake(id='experience-1', goal_id='goal-1'),
        ]

        result = self.subject.execute(ACCOUNT_ID, SKILL_ID)

        assert [item.goal_id for item in result] == ['goal-1', 'goal-2']

    def test_should_query_only_the_goal_ids_of_the_account(self) -> None:
        own_goal = GoalFaker.fake(id='goal-own', account_id=ACCOUNT_ID)
        self.repositories.goals.find_many_by_account_id.return_value = [own_goal]
        self.repositories.skill_experiences.find_many_by_goal_ids_and_skill_id.return_value = [
            SkillExperienceFaker.fake(id='experience-own', goal_id='goal-own'),
            SkillExperienceFaker.fake(id='experience-foreign', goal_id='goal-foreign'),
        ]

        result = self.subject.execute(ACCOUNT_ID, SKILL_ID)

        assert [item.skill_experience_id for item in result] == ['experience-own']
        self.repositories.goals.find_many_by_account_id.assert_called_once_with(
            ACCOUNT_ID
        )
        self.repositories.skill_experiences.find_many_by_goal_ids_and_skill_id.assert_called_once_with(
            ['goal-own'], SKILL_ID
        )

    def test_should_return_an_empty_list_for_an_unknown_skill(self) -> None:
        self.repositories.goals.find_many_by_account_id.return_value = [
            GoalFaker.fake(id='goal-1', account_id=ACCOUNT_ID)
        ]
        self.repositories.skill_experiences.find_many_by_goal_ids_and_skill_id.return_value = []

        result = self.subject.execute(ACCOUNT_ID, 'unknown-skill')

        assert result == []
        self.repositories.skill_experiences.find_many_by_goal_ids_and_skill_id.assert_called_once_with(
            ['goal-1'], 'unknown-skill'
        )
