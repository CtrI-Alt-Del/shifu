from math import isclose, isfinite, sqrt

from shifu.shared.core.domain.structures import structure

PLANNING_EMBEDDING_DIMENSION = 384


@structure
class PlanningIndexedEmbedding:
    skill_id: str
    vector: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.skill_id:
            raise ValueError('An indexed embedding needs a Skill identifier.')
        if len(self.vector) != PLANNING_EMBEDDING_DIMENSION or not all(
            isfinite(value) for value in self.vector
        ):
            raise ValueError('Invalid embedding dimensions or values.')
        norm = sqrt(sum(value * value for value in self.vector))
        if not isclose(norm, 1.0, rel_tol=1e-4, abs_tol=1e-4):
            raise ValueError('An indexed embedding must be normalized.')
