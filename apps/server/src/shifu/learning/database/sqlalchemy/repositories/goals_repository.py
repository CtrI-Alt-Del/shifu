from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shifu.learning.core.domain.entities import Goal
from shifu.learning.database.sqlalchemy.mappers import GoalMapper
from shifu.learning.database.sqlalchemy.models import GoalModel


class SqlalchemyGoalsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_id(self, goal_id: str) -> Goal | None:
        model = self._session.scalar(select(GoalModel).where(GoalModel.id == goal_id))
        return GoalMapper.to_domain(model) if model is not None else None

    def find_many_by_account_id(self, account_id: str) -> list[Goal]:
        models = self._session.scalars(
            select(GoalModel)
            .where(GoalModel.account_id == account_id)
            .order_by(GoalModel.created_at)
        ).all()
        return [GoalMapper.to_domain(model) for model in models]

    def add(self, goal: Goal) -> None:
        self._session.add(GoalMapper.to_model(goal))

    def add_many(self, goals: list[Goal]) -> None:
        self._session.add_all([GoalMapper.to_model(goal) for goal in goals])
        self._session.flush()

    def update(self, goal: Goal) -> None:
        self._session.merge(GoalMapper.to_model(goal))

    def remove(self, goal: Goal) -> None:
        self._session.execute(delete(GoalModel).where(GoalModel.id == goal.id))

    def remove_all(self) -> None:
        self._session.execute(delete(GoalModel))
