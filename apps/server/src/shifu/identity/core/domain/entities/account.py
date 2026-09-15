from datetime import datetime

from shifu.identity.core.domain.enums import AccountDeletionReason, AccountStatus
from shifu.shared.core.domain.entities import entity


@entity
class Account:
    id: str
    display_name: str
    email: str
    password_hash: str
    status: AccountStatus
    access_version: int
    time_zone: str | None
    created_at: datetime
    updated_at: datetime
    confirmed_at: datetime | None = None
    deleted_at: datetime | None = None
    deletion_reason: AccountDeletionReason | None = None
