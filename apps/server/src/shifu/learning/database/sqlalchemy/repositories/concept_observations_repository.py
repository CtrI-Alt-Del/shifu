from sqlalchemy import select
from sqlalchemy.orm import Session

from shifu.learning.core.domain.structures import ConceptObservation
from shifu.learning.database.sqlalchemy.mappers.concept_observation_mapper import (
    ConceptObservationMapper,
)
from shifu.learning.database.sqlalchemy.models.concept_observation_model import (
    ConceptObservationModel,
)


class SqlalchemyConceptObservationsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_many_by_skill_experience_id(
        self, skill_experience_id: str
    ) -> list[ConceptObservation]:
        models = self._session.scalars(
            select(ConceptObservationModel)
            .where(ConceptObservationModel.skill_experience_id == skill_experience_id)
            .order_by(
                ConceptObservationModel.completed_at, ConceptObservationModel.attempt_id
            )
        ).all()
        return [ConceptObservationMapper.to_domain(model) for model in models]

    def find_many_by_attempt_id(self, attempt_id: str) -> list[ConceptObservation]:
        models = self._session.scalars(
            select(ConceptObservationModel).where(
                ConceptObservationModel.attempt_id == attempt_id
            )
        ).all()
        return [ConceptObservationMapper.to_domain(model) for model in models]

    def add_many(
        self,
        skill_experience_id: str,
        competency_id: str,
        observations: tuple[ConceptObservation, ...],
    ) -> None:
        self._session.add_all(
            [
                ConceptObservationMapper.to_model(
                    skill_experience_id, competency_id, observation
                )
                for observation in observations
            ]
        )
