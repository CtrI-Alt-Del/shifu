from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shifu.curriculum.core.domain.entities import Concept
from shifu.curriculum.database.sqlalchemy.mappers import ConceptMapper
from shifu.curriculum.database.sqlalchemy.models import ConceptModel, CompetencyModel


class SqlalchemyConceptsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_many_by_skill_id(self, skill_id: str) -> list[Concept]:
        models = self._session.scalars(
            select(ConceptModel)
            .join(CompetencyModel, ConceptModel.competency_id == CompetencyModel.id)
            .where(CompetencyModel.skill_id == skill_id)
            .order_by(CompetencyModel.position, ConceptModel.position)
        ).all()
        return [ConceptMapper.to_domain(model) for model in models]

    def add_many(self, concepts: list[Concept]) -> None:
        self._session.add_all([ConceptMapper.to_model(concept) for concept in concepts])
        self._session.flush()

    def remove_all(self) -> None:
        self._session.execute(delete(ConceptModel))
