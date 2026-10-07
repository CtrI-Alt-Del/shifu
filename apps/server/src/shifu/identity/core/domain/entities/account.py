from datetime import datetime

from shifu.identity.core.domain.enums import AccountDeletionReason, AccountStatus
from shifu.identity.core.domain.errors import (
    AccountConfirmationNotAllowedError,
    AccountDeletionNotAllowedError,
    InvalidDisplayNameError,
    InvalidEmailError,
    InvalidPasswordError,
)
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.structures import EmailAddress, NonEmptyText


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

    def __post_init__(self) -> None:
        self.display_name = NonEmptyText.create(
            self.display_name, error_type=InvalidDisplayNameError
        ).value
        self.email = EmailAddress.create(self.email, error_type=InvalidEmailError).value
        if self.status is AccountStatus.PENDING_CONFIRMATION and self.confirmed_at:
            raise AccountConfirmationNotAllowedError

        if self.status is AccountStatus.ACTIVE and (
            self.confirmed_at is None
            or self.deleted_at is not None
            or self.deletion_reason is not None
        ):
            raise AccountConfirmationNotAllowedError

        if self.status is AccountStatus.DELETED and (
            self.deleted_at is None or self.deletion_reason is None
        ):
            raise AccountDeletionNotAllowedError

    @classmethod
    def create(
        cls,
        *,
        id: str,
        display_name: str,
        email: str,
        password_hash: str,
        status: AccountStatus,
        access_version: int,
        time_zone: str | None,
        created_at: datetime,
        updated_at: datetime,
        confirmed_at: datetime | None = None,
        deleted_at: datetime | None = None,
        deletion_reason: AccountDeletionReason | None = None,
    ) -> 'Account':
        return cls(
            id=id,
            display_name=display_name,
            email=email,
            password_hash=password_hash,
            status=status,
            access_version=access_version,
            time_zone=time_zone,
            created_at=created_at,
            updated_at=updated_at,
            confirmed_at=confirmed_at,
            deleted_at=deleted_at,
            deletion_reason=deletion_reason,
        )

    def confirm(self, confirmed_at: datetime) -> None:
        if self.status is not AccountStatus.PENDING_CONFIRMATION:
            raise AccountConfirmationNotAllowedError

        self.status = AccountStatus.ACTIVE
        self.access_version += 1
        self.confirmed_at = confirmed_at
        self.updated_at = confirmed_at

    def expire(self, expired_at: datetime) -> None:
        if self.status is not AccountStatus.PENDING_CONFIRMATION:
            raise AccountDeletionNotAllowedError

        self.status = AccountStatus.DELETED
        self.access_version += 1
        self.deleted_at = expired_at
        self.deletion_reason = AccountDeletionReason.UNCONFIRMED_ACCOUNT_EXPIRED
        self.updated_at = expired_at

    def delete(
        self,
        deleted_at: datetime,
        reason: AccountDeletionReason = AccountDeletionReason.USER_REQUESTED,
    ) -> None:
        if self.status is not AccountStatus.ACTIVE:
            raise AccountDeletionNotAllowedError

        self.status = AccountStatus.DELETED
        self.deleted_at = deleted_at
        self.deletion_reason = reason
        self.updated_at = deleted_at

    def change_display_name(self, display_name: str, updated_at: datetime) -> None:
        if self.status is not AccountStatus.ACTIVE:
            raise AccountConfirmationNotAllowedError

        self.display_name = NonEmptyText.create(
            display_name, error_type=InvalidDisplayNameError
        ).value
        self.updated_at = updated_at

    def invalidate_other_accesses(self, updated_at: datetime) -> None:
        self.access_version += 1
        self.updated_at = updated_at

    def replace_password(self, password_hash: str, updated_at: datetime) -> None:
        if not password_hash:
            raise InvalidPasswordError

        self.password_hash = password_hash
        self.access_version += 1
        self.updated_at = updated_at
