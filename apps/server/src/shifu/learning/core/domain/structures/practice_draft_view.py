from shifu.learning.core.domain.structures.practice_photo_view import PracticePhotoView
from shifu.shared.core.domain.structures import structure


@structure
class PracticeDraftView:
    revision: int
    reflection: str
    photos: tuple[PracticePhotoView, ...]
