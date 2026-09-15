from datetime import datetime

from shifu.identity.core.domain.enums import AccountStatus
from shifu.shared.core.domain.structures import structure


@structure
class AccountProfile:
    account_id: str
    display_name: str
    email: str
    time_zone: str | None
    status: AccountStatus
    created_at: datetime
    confirmed_at: datetime | None
