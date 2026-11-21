from typing import Literal

from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.curriculum.core.domain.structures.choice_concept_criterion import (
    ChoiceConceptCriterion,
)
from shifu.curriculum.core.domain.structures.ordering_step import OrderingStep
from shifu.shared.core.domain.structures import NonEmptyText, structure


@structure
class OrderingQuestion:
    key: str
    prompt: str
    steps: tuple[OrderingStep, ...]
    accepted_orders: tuple[tuple[str, ...], ...]
    correct_explanation: str
    incorrect_explanation: str
    concept_criteria: tuple[ChoiceConceptCriterion, ...]
    kind: Literal['ordering'] = 'ordering'

    def __post_init__(self) -> None:
        for name in ('key', 'prompt', 'correct_explanation', 'incorrect_explanation'):
            object.__setattr__(
                self,
                name,
                NonEmptyText.create(
                    getattr(self, name), error_type=InvalidActivityError
                ).value,
            )

        step_keys = tuple(step.key for step in self.steps)
        step_texts = tuple(step.text.casefold() for step in self.steps)
        if (
            not 3 <= len(self.steps) <= 8
            or len(step_keys) != len(set(step_keys))
            or len(step_texts) != len(set(step_texts))
            or not self.accepted_orders
            or not self.concept_criteria
        ):
            raise InvalidActivityError

        valid_keys = set(step_keys)
        normalized_orders: set[tuple[str, ...]] = set()
        for order in self.accepted_orders:
            if len(order) != len(step_keys) or set(order) != valid_keys:
                raise InvalidActivityError
            if order in normalized_orders:
                raise InvalidActivityError
            normalized_orders.add(order)

        if len(normalized_orders) == _permutation_count(len(step_keys)):
            raise InvalidActivityError


def _permutation_count(size: int) -> int:
    result = 1
    for factor in range(2, size + 1):
        result *= factor
    return result
