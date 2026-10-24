from typing import ClassVar

from shifu.intelligence.core.domain.enums.learner_memory_category import (
    LearnerMemoryCategory,
)
from shifu.intelligence.core.domain.structures.learner_memory_concept import (
    LearnerMemoryConcept,
)
from shifu.shared.core.domain.structures import structure


@structure
class LearnerMemoryStatement:
    MAX_CONTENT_CODE_POINTS: ClassVar[int] = 280
    MAX_CONCEPTS: ClassVar[int] = 3

    category: LearnerMemoryCategory
    content: str  # cleaned sentence
    concepts: tuple[LearnerMemoryConcept, ...]

    def __post_init__(self) -> None:
        if (
            not 1 <= len(self.content) <= self.MAX_CONTENT_CODE_POINTS
            or len(self.concepts) > self.MAX_CONCEPTS
        ):
            raise ValueError('Invalid learner memory statement')
