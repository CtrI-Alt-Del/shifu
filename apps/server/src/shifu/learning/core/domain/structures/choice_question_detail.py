from typing import Literal

from shifu.learning.core.domain.structures.choice_option_detail import (
    ChoiceOptionDetail,
)
from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import require_non_empty


@structure
class ChoiceQuestionDetail:
    key: str
    kind: Literal['single_choice', 'multiple_selection']
    prompt: str
    options: tuple[ChoiceOptionDetail, ...]

    def __post_init__(self) -> None:
        for name in ('key', 'prompt'):
            object.__setattr__(
                self, name, require_non_empty(getattr(self, name), ValidationError)
            )
