from datetime import datetime

from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
)
from shifu.identity.core.domain.errors import (
    AccountActionTokenAlreadyUsedError,
    AccountActionTokenExpiredError,
    AccountActionTokenInvalidatedError,
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

    def use(self, used_at: datetime) -> None:
        if self.status is AccountActionTokenStatus.USED:
            raise AccountActionTokenAlreadyUsedError
        if self.status is AccountActionTokenStatus.INVALIDATED:
            raise AccountActionTokenInvalidatedError
        if used_at >= self.expires_at:
            self.status = AccountActionTokenStatus.EXPIRED
            raise AccountActionTokenExpiredError
        self.status = AccountActionTokenStatus.USED
        self.used_at = used_at
        self.updated_at = used_at

    def invalidate(self, invalidated_at: datetime) -> None:
        if self.status is not AccountActionTokenStatus.PENDING:
            raise AccountActionTokenInvalidatedError
        self.status = AccountActionTokenStatus.INVALIDATED
        self.invalidated_at = invalidated_at
        self.updated_at = invalidated_at
