from shifu.shared.core.domain.structures import structure


@structure
class FillBlanksPlacement:
    blank_key: str
    word_key: str
