from shifu.curriculum.core.domain.entities import Competency
from shifu.curriculum.database.sqlalchemy.models import CompetencyModel


class CompetencyMapper:
    @staticmethod
    def to_domain(model: CompetencyModel) -> Competency:
        return Competency(
            id=model.id,
            skill_id=model.skill_id,
            name=model.name,
            description=model.description,
            position=model.position,
        )

    @staticmethod
    def to_model(competency: Competency) -> CompetencyModel:
        return CompetencyModel(
            id=competency.id,
            skill_id=competency.skill_id,
            name=competency.name,
            description=competency.description,
            position=competency.position,
        )
