from shifu.shared.core.domain.structures import structure

from .curriculum_sequence_item import CurriculumSequenceItem


@structure
class CurriculumSequence:
    competency_id: str
    items: tuple[CurriculumSequenceItem, ...]
