from shifu.learning.core.domain.entities import Goal
from shifu.learning.database.sqlalchemy.models import GoalModel


class GoalMapper:
    @staticmethod
    def to_domain(model: GoalModel) -> Goal:
        return Goal(
            id=model.id,
            account_id=model.account_id,
            title=model.title,
            description=model.description,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(goal: Goal) -> GoalModel:
        return GoalModel(
            id=goal.id,
            account_id=goal.account_id,
            title=goal.title,
            description=goal.description,
            created_at=goal.created_at,
            updated_at=goal.updated_at,
        )
