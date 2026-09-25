from typing import Literal

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.structures.curriculum_choice_option_snapshot import (
    CurriculumChoiceOptionSnapshot,
)
from shifu.shared.core.domain.structures.curriculum_choice_concept_criterion_snapshot import (
    CurriculumChoiceConceptCriterionSnapshot,
)
from shifu.shared.core.domain.validation import require_non_empty


@structure
class CurriculumChoiceQuestionSnapshot:
    key: str
    kind: Literal['single_choice', 'multiple_selection']
    prompt: str
    options: tuple[CurriculumChoiceOptionSnapshot, ...]
    correct_explanation: str
    incorrect_explanation: str
    concept_criteria: tuple[CurriculumChoiceConceptCriterionSnapshot, ...] = ()

    def __post_init__(self) -> None:
        for name in ('key', 'prompt', 'correct_explanation', 'incorrect_explanation'):
            object.__setattr__(
                self, name, require_non_empty(getattr(self, name), ValidationError)
            )
