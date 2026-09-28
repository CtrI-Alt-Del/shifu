from enum import StrEnum


class AccountActionTokenCancellationReason(StrEnum):
    CONFIRMED = 'confirmed'
    REISSUED = 'reissued'
    EXPIRED = 'expired'
    RESET = 'reset'
