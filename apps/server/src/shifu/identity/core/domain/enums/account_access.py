from enum import StrEnum


class AccountAccess(StrEnum):
    ACTIVATION_ONLY = 'activation-only'
    PROTECTED = 'protected'
