from enum import StrEnum


class AccountActionTokenStatus(StrEnum):
    PENDING = 'pending'
    USED = 'used'
    INVALIDATED = 'invalidated'
    EXPIRED = 'expired'
