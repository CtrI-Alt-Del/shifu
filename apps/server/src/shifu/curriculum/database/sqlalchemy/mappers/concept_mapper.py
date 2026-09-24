from typing import cast

from shifu.curriculum.core.domain.entities import Concept
from shifu.curriculum.database.sqlalchemy.models import ConceptModel


class ConceptMapper:
    @staticmethod
    def to_domain(model: ConceptModel) -> Concept:
        return Concept(
            id=model.id,
            competency_id=model.competency_id,
            name=model.name,
            description=model.description,
            position=model.position,
            observation_criteria=model.observation_criteria,
            prerequisite_ids=tuple(cast('list[str]', model.prerequisite_ids)),
        )

    @staticmethod
    def to_model(concept: Concept) -> ConceptModel:
        return ConceptModel(
            id=concept.id,
            competency_id=concept.competency_id,
            name=concept.name,
            description=concept.description,
            position=concept.position,
            observation_criteria=concept.observation_criteria,
            prerequisite_ids=list(concept.prerequisite_ids),
        )
