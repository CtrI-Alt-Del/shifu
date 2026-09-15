from shifu.shared.core.domain.structures import structure


@structure
class ActivitySequenceItem:
    position: int
    activity_id: str
