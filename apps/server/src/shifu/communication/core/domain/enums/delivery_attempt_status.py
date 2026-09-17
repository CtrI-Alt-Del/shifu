from enum import StrEnum


class DeliveryAttemptStatus(StrEnum):
    STARTED = 'started'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'
