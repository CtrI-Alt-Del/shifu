from enum import StrEnum


class AccountConfirmationCancellationReason(StrEnum):
    CONFIRMED = 'confirmed'
    REISSUED = 'reissued'
    EXPIRED = 'expired'
