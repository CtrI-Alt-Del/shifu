from datetime import datetime

from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
)
from shifu.shared.core.domain.entities import entity


@entity
class AccountActionToken:
    id: str
    account_id: str
    type: AccountActionTokenType
    status: AccountActionTokenStatus
    token_hash: str
    issued_at: datetime
    expires_at: datetime
    updated_at: datetime
    used_at: datetime | None = None
    invalidated_at: datetime | None = None
