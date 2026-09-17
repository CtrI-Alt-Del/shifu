from shifu.curriculum.core.domain.structures import SkillFoundation
from shifu.curriculum.database.sqlalchemy.models import SkillFoundationModel


class SkillFoundationMapper:
    @staticmethod
    def to_domain(model: SkillFoundationModel) -> SkillFoundation:
        return SkillFoundation(
            skill_id=model.skill_id,
            foundation_skill_id=model.foundation_skill_id,
        )

    @staticmethod
    def to_model(foundation: SkillFoundation) -> SkillFoundationModel:
        return SkillFoundationModel(
            skill_id=foundation.skill_id,
            foundation_skill_id=foundation.foundation_skill_id,
        )
