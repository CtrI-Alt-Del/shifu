from shifu.learning.core.domain.errors import SkillExperienceNotFoundError
from shifu.learning.core.interfaces import LearningDatabase


class RemoveSkillFromGoalUseCase:
    def __init__(self, learning_database: LearningDatabase) -> None:
        self._learning_database = learning_database

    def execute(self, account_id: str, goal_id: str, skill_id: str) -> None:
        with self._learning_database.transaction() as repositories:
            experience = (
                repositories.skill_experiences.find_by_goal_id_and_skill_id_for_update(
                    goal_id,
                    skill_id,
                )
            )
            if experience is None:
                raise SkillExperienceNotFoundError
            goal = repositories.goals.find_by_id(goal_id)
            if goal is None or goal.account_id != account_id:
                raise SkillExperienceNotFoundError
            repositories.skill_experiences.remove(experience)
