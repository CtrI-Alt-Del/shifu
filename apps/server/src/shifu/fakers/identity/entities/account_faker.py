from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from faker import Faker

from shifu.identity.core.domain.entities import Account
from shifu.identity.core.domain.enums import AccountDeletionReason, AccountStatus
from shifu.fakers.shared.id_provider_faker import IdProviderFaker

if TYPE_CHECKING:
    from collections.abc import Callable


class AccountFaker:
    _faker: Faker = Faker('pt_BR')
    _id_provider: IdProviderFaker = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        display_name: str | None = None,
        email: str | None = None,
        password_hash: str | None = None,
        status: AccountStatus = AccountStatus.ACTIVE,
        access_version: int | None = None,
        time_zone: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        confirmed_at: datetime | None = None,
        deleted_at: datetime | None = None,
        deletion_reason: AccountDeletionReason | None = None,
    ) -> Account:
        created = created_at or cls._faker.date_time(tzinfo=UTC)
        resolved_access_version = (
            access_version
            if access_version is not None
            else cls._faker.pyint(min_value=1, max_value=10)
        )
        resolved_confirmed_at = (
            confirmed_at
            if confirmed_at is not None
            else created
            if status is AccountStatus.ACTIVE
            else None
        )
        resolved_deleted_at = (
            deleted_at
            if deleted_at is not None
            else created
            if status is AccountStatus.DELETED
            else None
        )
        resolved_deletion_reason = (
            deletion_reason
            if deletion_reason is not None
            else AccountDeletionReason.USER_REQUESTED
            if status is AccountStatus.DELETED
            else None
        )
        return Account(
            id=id or cls._id_provider.generate(),
            display_name=(
                display_name if display_name is not None else cls._faker.name()
            ),
            email=email if email is not None else cls._faker.email(),
            password_hash=(
                password_hash
                if password_hash is not None
                else cls._faker.sha256(raw_output=False)
            ),
            status=status,
            access_version=resolved_access_version,
            time_zone=time_zone or cls._faker.timezone(),
            created_at=created,
            updated_at=updated_at or created,
            confirmed_at=resolved_confirmed_at,
            deleted_at=resolved_deleted_at,
            deletion_reason=resolved_deletion_reason,
        )

    @classmethod
    def fake_many(
        cls,
        count: int = 10,
        **overrides: object,
    ) -> list[Account]:
        fake = cast('Callable[..., Account]', cls.fake)
        return [fake(**overrides) for _ in range(count)]
