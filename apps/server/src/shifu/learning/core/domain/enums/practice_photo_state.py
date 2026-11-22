from enum import StrEnum


class PracticePhotoState(StrEnum):
    UPLOADING = 'uploading'
    READY = 'ready'
    FAILED = 'failed'
    REMOVED = 'removed'
