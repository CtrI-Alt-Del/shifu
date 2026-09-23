from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import require_non_empty

from .choice_option import ChoiceOption


@structure
class SingleChoiceQuestion:
    key: str
    prompt: str
    options: tuple[ChoiceOption, ...]
    correct_explanation: str | None = None
    incorrect_explanation: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, 'key', require_non_empty(self.key, InvalidActivityError)
        )
        object.__setattr__(
            self, 'prompt', require_non_empty(self.prompt, InvalidActivityError)
        )
        if sum(option.is_correct for option in self.options) != 1:
            raise InvalidActivityError
        for name in ('correct_explanation', 'incorrect_explanation'):
            explanation = getattr(self, name)
            if explanation is not None:
                object.__setattr__(
                    self, name, require_non_empty(explanation, InvalidActivityError)
                )
