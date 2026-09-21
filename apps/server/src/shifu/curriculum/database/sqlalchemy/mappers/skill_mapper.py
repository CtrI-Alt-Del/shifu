from shifu.curriculum.core.domain.entities import Skill
from shifu.curriculum.database.sqlalchemy.models import SkillModel


class SkillMapper:
    @staticmethod
    def to_domain(model: SkillModel) -> Skill:
        return Skill(id=model.id, name=model.name, description=model.description)

    @staticmethod
    def to_model(skill: Skill) -> SkillModel:
        return SkillModel(id=skill.id, name=skill.name, description=skill.description)
