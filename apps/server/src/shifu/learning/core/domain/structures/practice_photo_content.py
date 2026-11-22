from shifu.shared.core.domain.structures import structure


@structure
class PracticePhotoContent:
    media_type: str
    content: bytes
