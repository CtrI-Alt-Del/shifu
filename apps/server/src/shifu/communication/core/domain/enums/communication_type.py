from enum import StrEnum


class CommunicationType(StrEnum):
    ACCOUNT_CONFIRMATION = 'account-confirmation'
    PASSWORD_RECOVERY = 'password-recovery'
    ACCOUNT_ERASURE_ALERT = 'account-erasure-alert'
