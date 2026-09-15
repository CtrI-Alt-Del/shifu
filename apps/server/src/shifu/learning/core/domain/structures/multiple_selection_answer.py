from shifu.shared.core.domain.structures import structure


@structure
class MultipleSelectionAnswer:
    question_key: str
    selected_option_keys: tuple[str, ...]
