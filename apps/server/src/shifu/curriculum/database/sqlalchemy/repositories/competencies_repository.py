from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shifu.curriculum.core.domain.entities import Competency
from shifu.curriculum.database.sqlalchemy.mappers import CompetencyMapper
from shifu.curriculum.database.sqlalchemy.models import CompetencyModel


class SqlalchemyCompetenciesRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_id(self, competency_id: str) -> Competency | None:
        model = self._session.scalar(
            select(CompetencyModel).where(CompetencyModel.id == competency_id)
        )
        return CompetencyMapper.to_domain(model) if model is not None else None

    def find_many_by_skill_id(self, skill_id: str) -> list[Competency]:
        models = self._session.scalars(
            select(CompetencyModel)
            .where(CompetencyModel.skill_id == skill_id)
            .order_by(CompetencyModel.position)
        ).all()
        return [CompetencyMapper.to_domain(model) for model in models]

    def add_many(self, competencies: list[Competency]) -> None:
        self._session.add_all(
            [CompetencyMapper.to_model(competency) for competency in competencies]
        )
        self._session.flush()

    def remove_all(self) -> None:
        self._session.execute(delete(CompetencyModel))
