from shifu.learning.core.domain.enums import ActivityDifficulty
from shifu.shared.core.domain.structures import structure


@structure
class AdaptiveActivity:
    id: str
    competency_id: str
    position: int
    difficulty: ActivityDifficulty
    concept_ids: tuple[str, ...]
    required_concept_ids: tuple[str, ...] = ()
    question_count_by_concept: tuple[tuple[str, int], ...] = ()
    available: bool = True
    executable_concept_evidence: bool = True
