from shifu.shared.core.domain.structures import structure


@structure
class ChoiceAnswerSubmission:
    question_key: str
    selected_option_keys: tuple[str, ...]
