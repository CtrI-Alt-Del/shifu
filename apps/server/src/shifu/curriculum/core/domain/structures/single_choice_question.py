from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import NonEmptyText, structure

from .choice_option import ChoiceOption
from .choice_concept_criterion import ChoiceConceptCriterion


@structure
class SingleChoiceQuestion:
    key: str
    prompt: str
    options: tuple[ChoiceOption, ...]
    correct_explanation: str | None = None
    incorrect_explanation: str | None = None
    concept_criteria: tuple[ChoiceConceptCriterion, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            'key',
            NonEmptyText.create(self.key, error_type=InvalidActivityError).value,
        )
        object.__setattr__(
            self,
            'prompt',
            NonEmptyText.create(self.prompt, error_type=InvalidActivityError).value,
        )
        if sum(option.is_correct for option in self.options) != 1:
            raise InvalidActivityError
        for name in ('correct_explanation', 'incorrect_explanation'):
            explanation = getattr(self, name)
            if explanation is not None:
                object.__setattr__(
                    self,
                    name,
                    NonEmptyText.create(
                        explanation, error_type=InvalidActivityError
                    ).value,
                )
        concept_ids = tuple(item.concept_id for item in self.concept_criteria)
        if len(concept_ids) != len(set(concept_ids)):
            raise InvalidActivityError
