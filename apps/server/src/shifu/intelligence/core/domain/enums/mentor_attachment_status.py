from enum import StrEnum


class MentorAttachmentStatus(StrEnum):
    UPLOADING = 'uploading'
    PROCESSING = 'processing'
    READY = 'ready'
    PARTIAL = 'partial'
    FAILED = 'failed'
    REMOVED = 'removed'
