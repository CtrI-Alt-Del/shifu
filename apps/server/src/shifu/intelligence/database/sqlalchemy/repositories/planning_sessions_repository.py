from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shifu.intelligence.core.domain.entities import PlanningSession
from shifu.intelligence.database.sqlalchemy.mappers import PlanningSessionMapper
from shifu.intelligence.database.sqlalchemy.models import PlanningSessionModel


class SqlalchemyPlanningSessionsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, planning_session: PlanningSession) -> None:
        self._session.add(PlanningSessionMapper.to_model(planning_session))

    def find_by_id(self, planning_session_id: str) -> PlanningSession | None:
        model = self._session.scalar(
            select(PlanningSessionModel).where(
                PlanningSessionModel.id == planning_session_id
            )
        )
        return PlanningSessionMapper.to_domain(model) if model is not None else None

    def remove_all(self) -> None:
        self._session.execute(delete(PlanningSessionModel))
