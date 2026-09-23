from enum import StrEnum


class AccountConfirmationResultStatus(StrEnum):
    ACTIVATED = 'activated'
    EXPIRED = 'expired'
    USED = 'used'
    INVALID = 'invalid'
