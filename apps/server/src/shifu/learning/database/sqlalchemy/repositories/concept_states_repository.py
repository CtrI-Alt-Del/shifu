from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from shifu.learning.core.domain.structures import AdaptiveConceptState
from shifu.learning.database.sqlalchemy.mappers.concept_state_mapper import (
    ConceptStateMapper,
)
from shifu.learning.database.sqlalchemy.models.concept_state_model import (
    ConceptStateModel,
)


class SqlalchemyConceptStatesRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_many_by_skill_experience_id(
        self, skill_experience_id: str
    ) -> list[AdaptiveConceptState]:
        models = self._session.scalars(
            select(ConceptStateModel).where(
                ConceptStateModel.skill_experience_id == skill_experience_id
            )
        ).all()
        return [ConceptStateMapper.to_domain(model) for model in models]

    def upsert_many(
        self,
        skill_experience_id: str,
        competency_by_concept_id: dict[str, str],
        states: tuple[AdaptiveConceptState, ...],
        updated_at: datetime,
    ) -> None:
        for state in states:
            self._session.merge(
                ConceptStateMapper.to_model(
                    skill_experience_id,
                    competency_by_concept_id[state.concept_id],
                    state,
                    updated_at,
                )
            )
