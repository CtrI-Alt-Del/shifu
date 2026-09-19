from shifu.shared.core.domain.structures import structure


@structure
class SingleChoiceAnswer:
    question_key: str
    selected_option_key: str
