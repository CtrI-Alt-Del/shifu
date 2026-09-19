from shifu.curriculum.core.domain.enums import MaterialType
from shifu.curriculum.core.domain.errors import InvalidMaterialError
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.validation import require_non_empty


@entity
class Material:
    id: str
    skill_id: str
    title: str
    content: str
    material_type: MaterialType

    def __post_init__(self) -> None:
        self.title = require_non_empty(self.title, InvalidMaterialError)
        self.content = require_non_empty(self.content, InvalidMaterialError)

    @classmethod
    def create(
        cls,
        *,
        id: str,
        skill_id: str,
        title: str,
        content: str,
        material_type: MaterialType,
    ) -> 'Material':
        return cls(
            id=id,
            skill_id=skill_id,
            title=title,
            content=content,
            material_type=material_type,
        )
