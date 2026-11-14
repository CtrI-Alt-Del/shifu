from math import isfinite

from shifu.shared.core.domain.structures import structure


@structure
class PlanningEmbeddingMatch:
    skill_id: str
    similarity: float

    def __post_init__(self) -> None:
        if not self.skill_id:
            raise ValueError('A match needs a Skill identifier.')
        if not isfinite(self.similarity):
            raise ValueError('A similarity must be a finite number.')
