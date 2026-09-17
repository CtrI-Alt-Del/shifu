from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import structure

from .activity_sequence_item import ActivitySequenceItem
from .curriculum_sequence_item import CurriculumSequenceItem


@structure
class CurriculumSequence:
    competency_id: str
    items: tuple[CurriculumSequenceItem, ...]

    def __post_init__(self) -> None:
        positions = tuple(item.position for item in self.items)
        identifiers: tuple[str, ...] = tuple(
            item.activity_id
            if isinstance(item, ActivitySequenceItem)
            else item.material_id
            for item in self.items
        )
        if len(positions) != len(set(positions)) or len(identifiers) != len(
            set(identifiers)
        ):
            raise InvalidActivityError
