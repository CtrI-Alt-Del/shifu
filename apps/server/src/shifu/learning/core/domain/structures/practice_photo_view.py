from shifu.learning.core.domain.enums import PracticePhotoState
from shifu.shared.core.domain.structures import structure


@structure
class PracticePhotoView:
    record_key: str
    photo_id: str
    state: PracticePhotoState
    media_type: str
    size_bytes: int
