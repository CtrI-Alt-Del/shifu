from shifu.learning.core.domain.structures import GoalSummary
from shifu.learning.core.interfaces import LearningDatabase


class ListHomeGoalsUseCase:
    def __init__(self, database: LearningDatabase) -> None:
        self._database = database

    def execute(self, account_id: str) -> list[GoalSummary]:
        with self._database.transaction() as repositories:
            goals = repositories.goals.find_many_by_account_id(account_id)
            skill_counts = repositories.skill_experiences.count_many_by_goal_ids(
                [goal.id for goal in goals]
            )
            return [
                GoalSummary(
                    id=goal.id,
                    title=goal.title,
                    description=goal.description,
                    skill_count=skill_counts.get(goal.id, 0),
                    updated_at=goal.updated_at,
                )
                for goal in goals
            ]
