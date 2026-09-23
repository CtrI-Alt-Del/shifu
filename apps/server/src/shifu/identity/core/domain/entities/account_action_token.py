from datetime import datetime

from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
    AccountConfirmationDeliveryStatus,
)
from shifu.identity.core.domain.errors import (
    AccountActionTokenAlreadyUsedError,
    AccountConfirmationNotAllowedError,
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
    communication_id: str | None = None
    pending_handle_hash: str | None = None
    delivery_status: AccountConfirmationDeliveryStatus | None = None

    @property
    def identity_confirmation_id(self) -> str:
        return self.id

    def use(self, used_at: datetime) -> None:
        if self.status is AccountActionTokenStatus.USED:
            raise AccountActionTokenAlreadyUsedError
        if self.status is AccountActionTokenStatus.INVALIDATED:
            raise AccountActionTokenInvalidatedError
        if self.status is AccountActionTokenStatus.EXPIRED:
            raise AccountActionTokenExpiredError
        if used_at >= self.expires_at:
            self.expire(used_at)
            raise AccountActionTokenExpiredError
        self.status = AccountActionTokenStatus.USED
        self.used_at = used_at
        self.updated_at = used_at

    def expire(self, expired_at: datetime) -> bool:
        if self.status is AccountActionTokenStatus.EXPIRED:
            return False
        if self.status is not AccountActionTokenStatus.PENDING:
            raise AccountActionTokenInvalidatedError
        self.status = AccountActionTokenStatus.EXPIRED
        self.updated_at = expired_at
        return True

    def invalidate(self, invalidated_at: datetime) -> None:
        if self.status is not AccountActionTokenStatus.PENDING:
            raise AccountActionTokenInvalidatedError
        self.status = AccountActionTokenStatus.INVALIDATED
        self.invalidated_at = invalidated_at
        self.updated_at = invalidated_at

    def record_delivery_status(
        self,
        status: AccountConfirmationDeliveryStatus,
        recorded_at: datetime,
    ) -> bool:
        if self.type is not AccountActionTokenType.EMAIL_CONFIRMATION:
            raise AccountConfirmationNotAllowedError
        if self.delivery_status is status:
            return False
        if self.delivery_status in {
            AccountConfirmationDeliveryStatus.DELIVERED,
            AccountConfirmationDeliveryStatus.PERMANENT_FAILURE,
            AccountConfirmationDeliveryStatus.EXHAUSTED,
            AccountConfirmationDeliveryStatus.CANCELLED,
        }:
            return False
        self.delivery_status = status
        self.updated_at = recorded_at
        return True

    def replace_pending_handle_hash(
        self,
        pending_handle_hash: str,
        updated_at: datetime,
    ) -> None:
        if self.type is not AccountActionTokenType.EMAIL_CONFIRMATION:
            raise AccountConfirmationNotAllowedError
        if self.status is not AccountActionTokenStatus.PENDING:
            raise AccountActionTokenInvalidatedError
        self.pending_handle_hash = pending_handle_hash
        self.updated_at = updated_at
