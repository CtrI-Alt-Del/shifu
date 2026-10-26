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
    retained_session_id: str | None = None
    retained_session_access_version: int | None = None

    def __post_init__(self) -> None:
        self.display_name = NonEmptyText.create(
            self.display_name, error_type=InvalidDisplayNameError
        ).value
        self._validate_retained_session(self.access_version)
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
        retained_session_id: str | None = None,
        retained_session_access_version: int | None = None,
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
            retained_session_id=retained_session_id,
            retained_session_access_version=retained_session_access_version,
        )

    def confirm(self, confirmed_at: datetime) -> None:
        if self.status is not AccountStatus.PENDING_CONFIRMATION:
            raise AccountConfirmationNotAllowedError

        self.status = AccountStatus.ACTIVE
        self._clear_retained_session()
        self.access_version += 1
        self.confirmed_at = confirmed_at
        self.updated_at = confirmed_at

    def expire(self, expired_at: datetime) -> None:
        if self.status is not AccountStatus.PENDING_CONFIRMATION:
            raise AccountDeletionNotAllowedError

        self.status = AccountStatus.DELETED
        self._clear_retained_session()
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

        self._clear_retained_session()
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
        self._clear_retained_session()
        self.access_version += 1
        self.updated_at = updated_at

    def replace_password(
        self,
        password_hash: str,
        updated_at: datetime,
        *,
        retained_session_id: str | None = None,
        retained_session_access_version: int | None = None,
    ) -> None:
        if not password_hash:
            raise InvalidPasswordError

        previous_pair = (self.retained_session_id, self.retained_session_access_version)
        self.retained_session_id = retained_session_id
        self.retained_session_access_version = retained_session_access_version
        try:
            self._validate_retained_session(self.access_version + 1)
        except InvalidPasswordError:
            self.retained_session_id, self.retained_session_access_version = (
                previous_pair
            )
            raise
        self.password_hash = password_hash
        self.access_version += 1
        self.updated_at = updated_at

    def accepts_access(self, session_id: str, access_version: int) -> bool:
        return self.status is AccountStatus.ACTIVE and (
            access_version == self.access_version
            or (
                session_id == self.retained_session_id
                and access_version == self.retained_session_access_version
            )
        )

    def _clear_retained_session(self) -> None:
        self.retained_session_id = None
        self.retained_session_access_version = None

    def _validate_retained_session(self, version: int) -> None:
        if (
            self.retained_session_id is None
            and self.retained_session_access_version is None
        ):
            return
        if (
            not self.retained_session_id
            or self.retained_session_access_version is None
            or isinstance(self.retained_session_access_version, bool)
            or not 0 < self.retained_session_access_version < version
        ):
            raise InvalidPasswordError
