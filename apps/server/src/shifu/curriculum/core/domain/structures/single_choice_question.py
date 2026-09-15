from shifu.shared.core.domain.structures import structure

from .choice_option import ChoiceOption


@structure
class SingleChoiceQuestion:
    key: str
    prompt: str
    options: tuple[ChoiceOption, ...]
