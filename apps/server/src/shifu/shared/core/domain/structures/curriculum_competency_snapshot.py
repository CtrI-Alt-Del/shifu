from shifu.shared.core.domain.structures.curriculum_content_item import (
    CurriculumContentItem,
)
from shifu.shared.core.domain.structures.curriculum_content_validation import (
    require_positive_curriculum_position,
)
from shifu.shared.core.domain.structures.structure import structure


@structure
class CurriculumCompetencySnapshot:
    id: str
    skill_id: str
    name: str
    position: int
    items: tuple[CurriculumContentItem, ...]

    def __post_init__(self) -> None:
        require_positive_curriculum_position(self.position)
        positions = tuple(item.position for item in self.items)
        identifiers = tuple(item.id for item in self.items)
        if len(positions) != len(set(positions)):
            raise ValueError('Curriculum item positions must be unique.')
        if len(identifiers) != len(set(identifiers)):
            raise ValueError('Curriculum item identifiers must be unique.')
