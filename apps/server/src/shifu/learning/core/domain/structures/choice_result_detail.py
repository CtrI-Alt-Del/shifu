from decimal import Decimal

from shifu.shared.core.domain.structures import structure


@structure
class ChoiceResultDetail:
    question_key: str
    prompt: str
    selected_option_keys: tuple[str, ...]
    score: Decimal
    is_correct: bool
    explanation: str
    disclosed_correct_option_keys: tuple[str, ...] = ()
