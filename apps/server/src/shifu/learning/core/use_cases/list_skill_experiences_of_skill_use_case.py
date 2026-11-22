from shifu.learning.core.domain.structures import SkillExperienceReference
from shifu.learning.core.interfaces import LearningDatabase


class ListSkillExperiencesOfSkillUseCase:
    def __init__(self, learning_database: LearningDatabase) -> None:
        self._learning_database = learning_database

    def execute(self, account_id: str, skill_id: str) -> list[SkillExperienceReference]:
        with self._learning_database.transaction() as repositories:
            goals = repositories.goals.find_many_by_account_id(account_id)
            if not goals:
                return []

            goals_by_id = {goal.id: goal for goal in goals}
            experiences = (
                repositories.skill_experiences.find_many_by_goal_ids_and_skill_id(
                    list(goals_by_id), skill_id
                )
            )

        references = [
            SkillExperienceReference(
                goal_id=experience.goal_id,
                goal_title=goals_by_id[experience.goal_id].title,
                skill_experience_id=experience.id,
                skill_id=experience.skill_id,
                status=experience.status,
            )
            for experience in experiences
            if experience.goal_id in goals_by_id
        ]
        return sorted(references, key=lambda item: (item.goal_title, item.goal_id))
