from shifu.intelligence.core.domain.enums.learner_memory_category import (
    LearnerMemoryCategory,
)
from shifu.shared.core.domain.structures import structure


@structure
class LearnerMemoryContext:
    category: LearnerMemoryCategory
    content: str
