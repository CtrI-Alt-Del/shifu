from shifu.shared.core.domain.structures import structure


@structure
class OrderingAnswerSubmission:
    question_key: str
    ordered_step_keys: tuple[str, ...]
