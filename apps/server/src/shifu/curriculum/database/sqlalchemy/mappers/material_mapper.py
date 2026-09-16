from shifu.curriculum.core.domain.entities import Material
from shifu.curriculum.core.domain.enums import MaterialType
from shifu.curriculum.database.sqlalchemy.models import MaterialModel


class MaterialMapper:
    @staticmethod
    def to_domain(model: MaterialModel) -> Material:
        return Material(
            id=model.id,
            skill_id=model.skill_id,
            title=model.title,
            content=model.content,
            material_type=MaterialType(model.material_type),
        )

    @staticmethod
    def to_model(material: Material) -> MaterialModel:
        return MaterialModel(
            id=material.id,
            skill_id=material.skill_id,
            title=material.title,
            content=material.content,
            material_type=material.material_type.value,
        )
