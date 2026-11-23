from typing import Literal

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.curriculum_choice_concept_criterion_snapshot import (
    CurriculumChoiceConceptCriterionSnapshot,
)
from shifu.shared.core.domain.structures.curriculum_image_choice_option_snapshot import (
    CurriculumImageChoiceOptionSnapshot,
)
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.structure import structure

MIN_IMAGE_CHOICE_OPTIONS = 2
MAX_IMAGE_CHOICE_OPTIONS = 4


@structure
class CurriculumImageChoiceQuestionSnapshot:
    key: str
    kind: Literal['image_choice']
    prompt: str
    options: tuple[CurriculumImageChoiceOptionSnapshot, ...]
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
            raise ValidationError
