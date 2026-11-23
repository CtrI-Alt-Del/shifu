from typing import Literal

from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.curriculum.core.domain.structures.choice_concept_criterion import (
    ChoiceConceptCriterion,
)
from shifu.curriculum.core.domain.structures.image_choice_option import (
    ImageChoiceOption,
)
from shifu.shared.core.domain.structures import NonEmptyText, structure

MIN_IMAGE_CHOICE_OPTIONS = 2
MAX_IMAGE_CHOICE_OPTIONS = 4


@structure
class ImageChoiceQuestion:
    key: str
    prompt: str
    options: tuple[ImageChoiceOption, ...]
    correct_explanation: str
    incorrect_explanation: str
    concept_criteria: tuple[ChoiceConceptCriterion, ...]
    kind: Literal['image_choice'] = 'image_choice'

    def __post_init__(self) -> None:
        for name in ('key', 'prompt', 'correct_explanation', 'incorrect_explanation'):
            object.__setattr__(
                self,
                name,
                NonEmptyText.create(
                    getattr(self, name), error_type=InvalidActivityError
                ).value,
            )

        keys = tuple(option.key.casefold() for option in self.options)
        paths = tuple(option.image_path.casefold() for option in self.options)
        descriptions = tuple(option.description.casefold() for option in self.options)
        if (
            self.kind != 'image_choice'
            or not MIN_IMAGE_CHOICE_OPTIONS
            <= len(self.options)
            <= MAX_IMAGE_CHOICE_OPTIONS
            or sum(option.is_correct for option in self.options) != 1
            or len(set(keys)) != len(keys)
            or len(set(paths)) != len(paths)
            or len(set(descriptions)) != len(descriptions)
            or not self.concept_criteria
        ):
            raise InvalidActivityError
