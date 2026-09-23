from enum import StrEnum


class CommunicationDeliveryState(StrEnum):
    DELIVERED = 'delivered'
    TEMPORARY_FAILURE = 'temporary_failure'
    PERMANENT_FAILURE = 'permanent_failure'
    EXHAUSTED = 'exhausted'
    CANCELLED = 'cancelled'


DeliveryState = CommunicationDeliveryState
