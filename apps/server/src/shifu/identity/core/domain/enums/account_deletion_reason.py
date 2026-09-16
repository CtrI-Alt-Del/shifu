from enum import StrEnum


class AccountDeletionReason(StrEnum):
    USER_REQUESTED = 'user-requested'
    UNCONFIRMED_ACCOUNT_EXPIRED = 'unconfirmed-account-expired'
