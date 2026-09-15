from enum import StrEnum


class AccountStatus(StrEnum):
    PENDING_CONFIRMATION = 'pending-confirmation'
    ACTIVE = 'active'
    DELETED = 'deleted'
