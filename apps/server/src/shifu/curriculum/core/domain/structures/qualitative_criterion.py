from shifu.shared.core.domain.structures import structure


@structure
class QualitativeCriterion:
    name: str
    description: str
    weight_percentage: int
