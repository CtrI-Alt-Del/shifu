from typing import cast

from shifu.curriculum.core.domain.entities import Skill
from shifu.curriculum.database.sqlalchemy.models import SkillModel


class SkillMapper:
    @staticmethod
    def to_domain(model: SkillModel) -> Skill:
        return Skill(
            id=model.id,
            name=model.name,
            description=model.description,
            initial_diagnostic_activity_ids=tuple(
                cast('list[str]', model.initial_diagnostic_activity_ids)
            ),
        )

    @staticmethod
    def to_model(skill: Skill) -> SkillModel:
        return SkillModel(
            id=skill.id,
            name=skill.name,
            description=skill.description,
            initial_diagnostic_activity_ids=list(skill.initial_diagnostic_activity_ids),
        )
