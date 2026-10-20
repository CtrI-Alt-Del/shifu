from math import isfinite

from shifu.shared.core.domain.structures import structure


@structure
class PlanningSkillCandidate:
    skill_id: str
    name: str
    description: str
    foundation_skill_ids: tuple[str, ...]
    score: float
    lexical_rank: int | None
    semantic_rank: int | None

    def __post_init__(self) -> None:
        if not self.skill_id or not self.name:
            raise ValueError('A candidate needs a Skill identifier and name.')
        if not isfinite(self.score) or self.score <= 0:
            raise ValueError('A candidate score must be a positive number.')
        if self.lexical_rank is None and self.semantic_rank is None:
            raise ValueError('A candidate needs at least one source rank.')
        if len(set(self.foundation_skill_ids)) != len(self.foundation_skill_ids):
            raise ValueError('Foundation Skills cannot repeat.')
        if self.skill_id in self.foundation_skill_ids:
            raise ValueError('A Skill cannot be its own foundation.')
