from shifu.shared.core.domain.structures.curriculum_content_item import (
    CurriculumContentItem,
)
from shifu.shared.core.domain.structures.curriculum_concept_snapshot import (
    CurriculumConceptSnapshot,
)
from shifu.shared.core.domain.structures.curriculum_activity_snapshot import (
    CurriculumActivitySnapshot,
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
    concepts: tuple[CurriculumConceptSnapshot, ...] = ()
    diagnostic_activities: tuple[CurriculumActivitySnapshot, ...] = ()

    def __post_init__(self) -> None:
        require_positive_curriculum_position(self.position)
        positions = tuple(item.position for item in self.items)
        identifiers = tuple(item.id for item in self.items)
        if len(positions) != len(set(positions)):
            raise ValueError('Curriculum item positions must be unique.')
        if len(identifiers) != len(set(identifiers)):
            raise ValueError('Curriculum item identifiers must be unique.')
        concept_positions = tuple(concept.position for concept in self.concepts)
        concept_ids = tuple(concept.id for concept in self.concepts)
        if len(concept_positions) != len(set(concept_positions)) or len(
            concept_ids
        ) != len(set(concept_ids)):
            raise ValueError('Curriculum Concept positions and IDs must be unique.')
        if any(concept.competency_id != self.id for concept in self.concepts):
            raise ValueError('Curriculum Concept does not belong to Competency.')
