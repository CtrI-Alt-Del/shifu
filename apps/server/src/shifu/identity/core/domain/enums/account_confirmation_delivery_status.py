from enum import StrEnum


class AccountConfirmationDeliveryStatus(StrEnum):
    DELIVERY_UNAVAILABLE = 'delivery_unavailable'
    DELIVERED = 'delivered'
    TEMPORARY_FAILURE = 'temporary_failure'
    PERMANENT_FAILURE = 'permanent_failure'
    EXHAUSTED = 'exhausted'
    CANCELLED = 'cancelled'
