from shifu.curriculum.core.domain.errors import InvalidEvaluationRuleError
from shifu.shared.core.domain.structures import NonEmptyText, structure

from .translation_rubric_criterion import TranslationRubricCriterion

_REQUIRED_CRITERIA_WEIGHTS = {
    'semantic_preservation': 70,
    'grammatical_adequacy': 30,
}


@structure
class TranslationRubricEvaluationPart:
    question_key: str
    weight_percentage: int
    criteria: tuple[TranslationRubricCriterion, ...]

    def __post_init__(self) -> None:
        NonEmptyText.create(self.question_key, error_type=InvalidEvaluationRuleError)
        criteria_by_key = {criterion.key: criterion for criterion in self.criteria}
        if (
            len(self.criteria) != 2
            or set(criteria_by_key) != set(_REQUIRED_CRITERIA_WEIGHTS)
            or any(not criterion.required for criterion in self.criteria)
            or any(
                criteria_by_key[key].weight_percentage != weight
                for key, weight in _REQUIRED_CRITERIA_WEIGHTS.items()
            )
        ):
            raise InvalidEvaluationRuleError
