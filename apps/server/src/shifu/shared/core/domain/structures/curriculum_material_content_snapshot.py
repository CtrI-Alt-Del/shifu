from shifu.shared.core.domain.structures.structure import structure


@structure
class CurriculumMaterialContentSnapshot:
    id: str
    skill_id: str
    title: str
    material_type: str
    content: str

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError('Curriculum material titles cannot be empty.')
        if not self.content.strip():
            raise ValueError('Curriculum material content cannot be empty.')
