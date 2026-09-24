from shifu.learning.core.domain.errors import GoalNotFoundError
from shifu.learning.core.interfaces import LearningDatabase


class RemoveGoalUseCase:
    def __init__(
        self,
        learning_database: LearningDatabase,
    ) -> None:
        self._learning_database = learning_database

    def execute(
        self,
        account_id: str,
        goal_id: str,
    ) -> None:
        with self._learning_database.transaction() as repos:
            goal = repos.goals.find_by_id(goal_id)
            if goal is None or goal.account_id != account_id:
                raise GoalNotFoundError
            repos.goals.remove(goal)
