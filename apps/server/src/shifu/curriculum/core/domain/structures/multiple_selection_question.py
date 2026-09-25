from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import require_non_empty

from .choice_option import ChoiceOption
from .choice_concept_criterion import ChoiceConceptCriterion


@structure
class MultipleSelectionQuestion:
    key: str
    prompt: str
    options: tuple[ChoiceOption, ...]
    correct_explanation: str | None = None
    incorrect_explanation: str | None = None
    concept_criteria: tuple[ChoiceConceptCriterion, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, 'key', require_non_empty(self.key, InvalidActivityError)
        )
        object.__setattr__(
            self, 'prompt', require_non_empty(self.prompt, InvalidActivityError)
        )
        correct_count = sum(option.is_correct for option in self.options)
        if correct_count < 2 or correct_count == len(self.options):
            raise InvalidActivityError
        for name in ('correct_explanation', 'incorrect_explanation'):
            explanation = getattr(self, name)
            if explanation is not None:
                object.__setattr__(
                    self, name, require_non_empty(explanation, InvalidActivityError)
                )
        concept_ids = tuple(item.concept_id for item in self.concept_criteria)
        if len(concept_ids) != len(set(concept_ids)):
            raise InvalidActivityError
