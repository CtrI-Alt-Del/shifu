from shifu.learning.core.domain.errors import GoalNotFoundError
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.practice_photo_cleanup import PracticePhotoCleanup


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

            for experience in repos.skill_experiences.find_many_by_goal_id(goal.id):
                locked = repos.skill_experiences.find_by_id_for_update(experience.id)
                if locked is not None:
                    PracticePhotoCleanup.request_for_skill_experience(repos, locked.id)

            repos.goals.remove(goal)
