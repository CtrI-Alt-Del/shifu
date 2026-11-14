from math import isfinite

from shifu.shared.core.domain.structures import structure


@structure
class PlanningSkillRankEntry:
    skill_id: str
    score: float
    lexical_rank: int | None
    semantic_rank: int | None

    def __post_init__(self) -> None:
        if not self.skill_id:
            raise ValueError('A rank entry needs a Skill identifier.')
        if not isfinite(self.score) or self.score <= 0:
            raise ValueError('A fused score must be a positive number.')
        if self.lexical_rank is None and self.semantic_rank is None:
            raise ValueError('A rank entry needs at least one source rank.')
        for rank in (self.lexical_rank, self.semantic_rank):
            if rank is not None and rank < 1:
                raise ValueError('Ranks start at one.')
