from shifu.shared.core.domain.structures import structure
from shifu.learning.core.domain.structures.competency_content_concept import (
    CompetencyContentConcept,
)


@structure
class CompetencyMaterialDetail:
    id: str
    title: str
    position: int
    concepts: tuple[CompetencyContentConcept, ...] = ()

    def __post_init__(self) -> None:
        if self.position < 1:
            raise ValueError('Competency content positions must be positive.')
