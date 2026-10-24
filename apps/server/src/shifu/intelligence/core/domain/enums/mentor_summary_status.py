from enum import StrEnum


class MentorSummaryStatus(StrEnum):
    PROCESSING = 'processing'
    READY = 'ready'
    FAILED = 'failed'
