from shifu.intelligence.core.domain.entities.learner_memory import LearnerMemory
from shifu.intelligence.core.domain.structures.learner_memory_concept import (
    LearnerMemoryConcept,
)
from shifu.intelligence.core.domain.structures.learner_memory_origin_view import (
    LearnerMemoryOriginView,
)
from shifu.shared.core.domain.structures import structure


@structure
class LearnerMemoryDetails:
    memory: LearnerMemory
    origins: tuple[LearnerMemoryOriginView, ...]
    concepts: tuple[LearnerMemoryConcept, ...]
