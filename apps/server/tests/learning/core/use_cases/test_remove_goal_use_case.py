from unittest.mock import create_autospec

import pytest

from shifu.fakers.learning.entities import GoalFaker
from shifu.learning.core.domain.errors import GoalNotFoundError
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases import RemoveGoalUseCase

ACCOUNT_ID = 'account-1'
GOAL_ID = 'goal-1'


class TestRemoveGoalUseCase:
    def setup_method(self) -> None:
        self.learning_database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(
            LearningDatabaseRepositories,
            instance=True,
        )
        self.learning_database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.goals_repository = self.repositories.goals
        self.subject = RemoveGoalUseCase(self.learning_database)

    def test_should_remove_goal_when_owned_by_account(self) -> None:
        goal = GoalFaker.fake(id=GOAL_ID, account_id=ACCOUNT_ID)
        self.goals_repository.find_by_id.return_value = goal

        self.subject.execute(account_id=ACCOUNT_ID, goal_id=GOAL_ID)

        self.goals_repository.remove.assert_called_once_with(goal)

    def test_should_raise_goal_not_found_error_when_goal_missing(self) -> None:
        self.goals_repository.find_by_id.return_value = None

        with pytest.raises(GoalNotFoundError):
            self.subject.execute(account_id=ACCOUNT_ID, goal_id=GOAL_ID)

        self.goals_repository.remove.assert_not_called()

    def test_should_raise_goal_not_found_error_when_goal_belongs_to_another_account(
        self,
    ) -> None:
        goal = GoalFaker.fake(id=GOAL_ID, account_id='other-account')
        self.goals_repository.find_by_id.return_value = goal

        with pytest.raises(GoalNotFoundError):
            self.subject.execute(account_id=ACCOUNT_ID, goal_id=GOAL_ID)

        self.goals_repository.remove.assert_not_called()
