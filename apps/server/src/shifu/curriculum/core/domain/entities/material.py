from shifu.curriculum.core.domain.enums import MaterialType
from shifu.shared.core.domain.entities import entity


@entity
class Material:
    id: str
    skill_id: str
    title: str
    content: str
    material_type: MaterialType
