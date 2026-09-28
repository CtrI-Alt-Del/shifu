from enum import StrEnum


class AccountActionTokenDeliveryStatus(StrEnum):
    DELIVERY_UNAVAILABLE = 'delivery_unavailable'
    QUEUED = 'queued'
    DELIVERED = 'delivered'
    TEMPORARY_FAILURE = 'temporary_failure'
    PERMANENT_FAILURE = 'permanent_failure'
    EXHAUSTED = 'exhausted'
    CANCELLED = 'cancelled'
    EXPIRED = 'expired'
