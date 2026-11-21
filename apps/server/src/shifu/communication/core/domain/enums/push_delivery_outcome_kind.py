from enum import StrEnum


class PushDeliveryOutcomeKind(StrEnum):
    ACCEPTED = 'accepted'
    GONE = 'gone'
    TEMPORARY_FAILURE = 'temporary-failure'
    PERMANENT_FAILURE = 'permanent-failure'
