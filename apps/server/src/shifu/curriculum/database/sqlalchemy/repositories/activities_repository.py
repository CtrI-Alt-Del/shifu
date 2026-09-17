from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shifu.curriculum.core.domain.entities import Activity
from shifu.curriculum.database.sqlalchemy.mappers import ActivityMapper
from shifu.curriculum.database.sqlalchemy.models import ActivityModel


class SqlalchemyActivitiesRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_id(self, activity_id: str) -> Activity | None:
        model = self._session.scalar(
            select(ActivityModel).where(ActivityModel.id == activity_id)
        )
        return ActivityMapper.to_domain(model) if model is not None else None

    def find_many_by_ids(self, activity_ids: tuple[str, ...]) -> list[Activity]:
        models = self._session.scalars(
            select(ActivityModel).where(ActivityModel.id.in_(activity_ids))
        ).all()
        return [ActivityMapper.to_domain(model) for model in models]

    def find_many_by_competency_id(self, competency_id: str) -> list[Activity]:
        models = self._session.scalars(
            select(ActivityModel).where(ActivityModel.competency_id == competency_id)
        ).all()
        return [ActivityMapper.to_domain(model) for model in models]

    def add_many(self, activities: list[Activity]) -> None:
        self._session.add_all(
            [ActivityMapper.to_model(activity) for activity in activities]
        )
        self._session.flush()

    def remove_all(self) -> None:
        self._session.execute(delete(ActivityModel))
