from enum import StrEnum


class AccountActionTokenType(StrEnum):
    EMAIL_CONFIRMATION = 'email-confirmation'
    PASSWORD_RECOVERY = 'password-recovery'
