from shifu.shared.core.domain.structures import structure


@structure
class ChoiceOption:
    key: str
    text: str
    is_correct: bool
