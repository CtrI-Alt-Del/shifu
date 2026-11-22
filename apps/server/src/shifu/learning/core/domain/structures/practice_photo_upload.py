from shifu.shared.core.domain.structures import structure


@structure
class PracticePhotoUpload:
    filename: str
    media_type: str
    content: bytes
