from enum import StrEnum


class ConfirmationDeliveryQueueStatus(StrEnum):
    QUEUED = 'queued'
    DELIVERY_UNAVAILABLE = 'delivery_unavailable'
