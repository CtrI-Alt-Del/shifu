from shifu.shared.core.domain.structures import structure


@structure
class FillBlanksSegmentDetail:
    text: str | None = None
    blank_key: str | None = None
