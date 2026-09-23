from enum import StrEnum


class CommunicationCancellationReason(StrEnum):
    CONFIRMED = 'confirmed'
    REISSUED = 'reissued'
    EXPIRED = 'expired'


CancellationReason = CommunicationCancellationReason
