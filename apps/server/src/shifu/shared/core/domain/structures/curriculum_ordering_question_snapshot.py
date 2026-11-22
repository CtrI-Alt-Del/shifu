from typing import Literal

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.curriculum_choice_concept_criterion_snapshot import (
    CurriculumChoiceConceptCriterionSnapshot,
)
from shifu.shared.core.domain.structures.curriculum_ordering_step_snapshot import (
    CurriculumOrderingStepSnapshot,
)
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.structure import structure


@structure
class CurriculumOrderingQuestionSnapshot:
    key: str
    kind: Literal['ordering']
    prompt: str
    steps: tuple[CurriculumOrderingStepSnapshot, ...]
    accepted_orders: tuple[tuple[str, ...], ...]
    correct_explanation: str
    incorrect_explanation: str
    concept_criteria: tuple[CurriculumChoiceConceptCriterionSnapshot, ...]

    def __post_init__(self) -> None:
        for name in ('key', 'prompt', 'correct_explanation', 'incorrect_explanation'):
            object.__setattr__(
                self,
                name,
                NonEmptyText.create(
                    getattr(self, name), error_type=ValidationError
                ).value,
            )

        keys = tuple(step.key for step in self.steps)
        texts = tuple(step.text.casefold() for step in self.steps)
        accepted = set(self.accepted_orders)
        permutation_count = 1
        for factor in range(2, len(keys) + 1):
            permutation_count *= factor
        if (
            not 3 <= len(keys) <= 8
            or len(keys) != len(set(keys))
            or len(texts) != len(set(texts))
            or not self.accepted_orders
            or not self.concept_criteria
            or len(accepted) != len(self.accepted_orders)
            or any(
                len(order) != len(keys) or set(order) != set(keys) for order in accepted
            )
            or len(accepted) == permutation_count
        ):
            raise ValidationError
