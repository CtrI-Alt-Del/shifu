from unittest.mock import create_autospec

import pytest

from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.learning.core.domain.errors import SkillExperienceNotFoundError
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases import RemoveSkillFromGoalUseCase

ACCOUNT_ID = 'account-1'
GOAL_ID = 'goal-1'
SKILL_ID = 'skill-1'


class TestRemoveSkillFromGoalUseCase:
    def setup_method(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(
            LearningDatabaseRepositories,
            instance=True,
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.experiences = self.repositories.skill_experiences
        self.goals = self.repositories.goals
        self.subject = RemoveSkillFromGoalUseCase(self.database)

    def test_should_remove_owned_skill_experience(self) -> None:
        experience = SkillExperienceFaker.fake(
            goal_id=GOAL_ID,
            skill_id=SKILL_ID,
        )
        goal = GoalFaker.fake(id=GOAL_ID, account_id=ACCOUNT_ID)
        self.experiences.find_by_goal_id_and_skill_id_for_update.return_value = (
            experience
        )
        self.goals.find_by_id.return_value = goal

        self.subject.execute(ACCOUNT_ID, GOAL_ID, SKILL_ID)

        self.experiences.remove.assert_called_once_with(experience)

    def test_should_raise_private_not_found_when_experience_is_missing(self) -> None:
        self.experiences.find_by_goal_id_and_skill_id_for_update.return_value = None

        with pytest.raises(SkillExperienceNotFoundError):
            self.subject.execute(ACCOUNT_ID, GOAL_ID, SKILL_ID)

        self.goals.find_by_id.assert_not_called()
        self.experiences.remove.assert_not_called()

    @pytest.mark.parametrize('goal', [None, GoalFaker.fake(account_id='other-account')])
    def test_should_raise_private_not_found_when_goal_is_missing_or_not_owned(
        self,
        goal: object,
    ) -> None:
        experience = SkillExperienceFaker.fake(
            goal_id=GOAL_ID,
            skill_id=SKILL_ID,
        )
        self.experiences.find_by_goal_id_and_skill_id_for_update.return_value = (
            experience
        )
        self.goals.find_by_id.return_value = goal

        with pytest.raises(SkillExperienceNotFoundError):
            self.subject.execute(ACCOUNT_ID, GOAL_ID, SKILL_ID)

        self.experiences.remove.assert_not_called()
