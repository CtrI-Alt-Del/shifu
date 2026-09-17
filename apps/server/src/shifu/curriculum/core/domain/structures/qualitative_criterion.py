from shifu.curriculum.core.domain.errors import InvalidEvaluationRuleError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import require_non_empty


@structure
class QualitativeCriterion:
    name: str
    description: str
    weight_percentage: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self, 'name', require_non_empty(self.name, InvalidEvaluationRuleError)
        )
        object.__setattr__(
            self,
            'description',
            require_non_empty(self.description, InvalidEvaluationRuleError),
        )
