from shifu.shared.core.domain.structures.curriculum_content_validation import (
    require_positive_curriculum_position,
)
from shifu.shared.core.domain.structures.structure import structure


@structure
class CurriculumMaterialSnapshot:
    id: str
    title: str
    material_type: str
    position: int

    def __post_init__(self) -> None:
        require_positive_curriculum_position(self.position)
