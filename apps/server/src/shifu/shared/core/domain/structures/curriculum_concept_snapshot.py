from shifu.shared.core.domain.structures.curriculum_content_validation import (
    require_positive_curriculum_position,
)
from shifu.shared.core.domain.structures.structure import structure


@structure
class CurriculumConceptSnapshot:
    id: str
    competency_id: str
    name: str
    position: int
    prerequisite_ids: tuple[str, ...]
    observation_criteria: str

    def __post_init__(self) -> None:
        require_positive_curriculum_position(self.position)
        if not self.id or not self.name or not self.observation_criteria:
            raise ValueError('Curriculum concept is incomplete.')
