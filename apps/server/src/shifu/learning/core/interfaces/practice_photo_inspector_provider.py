from typing import Protocol


class PracticePhotoInspectorProvider(Protocol):
    def sanitize(self, content: bytes, media_type: str) -> bytes:
        """Return the photo re-encoded in the same format without metadata.

        Raise `PracticePhotoInvalidError` unless the bytes decode as the given type.
        """
        ...
