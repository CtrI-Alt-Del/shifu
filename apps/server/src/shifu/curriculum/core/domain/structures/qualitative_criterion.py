from shifu.curriculum.core.domain.errors import InvalidEvaluationRuleError
from shifu.shared.core.domain.structures import NonEmptyText, structure


@structure
class QualitativeCriterion:
    name: str
    description: str
    weight_percentage: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            'name',
            NonEmptyText.create(self.name, error_type=InvalidEvaluationRuleError).value,
        )
        object.__setattr__(
            self,
            'description',
            NonEmptyText.create(
                self.description, error_type=InvalidEvaluationRuleError
            ).value,
        )
