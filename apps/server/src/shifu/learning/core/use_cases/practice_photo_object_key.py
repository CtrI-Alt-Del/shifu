class PracticePhotoObjectKey:
    """Own the private object-key policy for practice photos."""

    _PREFIX = 'practice-photos/'
    _SUFFIX = '/original'

    @staticmethod
    def for_photo(photo_id: str) -> str:
        return f'{PracticePhotoObjectKey._PREFIX}{photo_id}{PracticePhotoObjectKey._SUFFIX}'

    @staticmethod
    def matches(photo_id: str, object_key: str) -> bool:
        return bool(photo_id) and object_key == PracticePhotoObjectKey.for_photo(
            photo_id
        )
