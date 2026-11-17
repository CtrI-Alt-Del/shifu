from shifu.shared.core.domain.structures import structure


@structure
class FillBlanksExpectedBlank:
    blank_key: str
    accepted_words: tuple[str, ...]
