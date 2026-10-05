from shifu.curriculum.core.domain.enums import MaterialType
from shifu.curriculum.core.domain.errors import InvalidMaterialError
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.structures import NonEmptyText


@entity
class Material:
    id: str
    skill_id: str
    title: str
    content: str
    material_type: MaterialType
    concept_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self.title = NonEmptyText.create(
            self.title, error_type=InvalidMaterialError
        ).value
        self.content = NonEmptyText.create(
            self.content, error_type=InvalidMaterialError
        ).value
        if len(self.concept_ids) != len(set(self.concept_ids)):
            raise InvalidMaterialError

    @classmethod
    def create(
        cls,
        *,
        id: str,
        skill_id: str,
        title: str,
        content: str,
        material_type: MaterialType,
        concept_ids: tuple[str, ...] = (),
    ) -> 'Material':
        return cls(
            id=id,
            skill_id=skill_id,
            title=title,
            content=content,
            material_type=material_type,
            concept_ids=concept_ids,
        )
