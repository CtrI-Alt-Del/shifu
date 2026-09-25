from shifu.shared.core.domain.structures.curriculum_content_validation import (
    require_positive_curriculum_position,
)
from shifu.shared.core.domain.structures.structure import structure


@structure
class CurriculumActivitySnapshot:
    id: str
    title: str
    activity_type: str
    difficulty: str
    position: int
    concept_ids: tuple[str, ...] = ()
    required_concept_ids: tuple[str, ...] = ()
    question_count_by_concept: tuple[tuple[str, int], ...] = ()
    maximum_evidence_by_concept: tuple[tuple[str, int], ...] = ()
    executable_concept_evidence: bool = False

    def __post_init__(self) -> None:
        require_positive_curriculum_position(self.position)
