from shifu.learning.core.domain.structures.skill_evolution_point import (
    SkillEvolutionPoint,
)
from shifu.shared.core.domain.structures import structure


@structure
class SkillEvolution:
    skill_experience_id: str
    points: tuple[SkillEvolutionPoint, ...]  # chronological
