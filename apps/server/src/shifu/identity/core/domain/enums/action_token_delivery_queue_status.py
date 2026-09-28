from enum import StrEnum


class ActionTokenDeliveryQueueStatus(StrEnum):
    QUEUED = 'queued'
    DELIVERY_UNAVAILABLE = 'delivery_unavailable'


ActionTokenQueueStatus = ActionTokenDeliveryQueueStatus
