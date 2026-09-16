from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from faker import Faker

from shifu.identity.core.domain.entities import Account
from shifu.identity.core.domain.enums import AccountDeletionReason, AccountStatus
from shifu.shared.core.interfaces.fakers import IdProviderFaker

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
        return Account(
            id=id or cls._id_provider.generate(),
            display_name=display_name or cls._faker.name(),
            email=email or cls._faker.email(),
            password_hash=password_hash or cls._faker.sha256(raw_output=False),
            status=status,
            access_version=access_version
            or cls._faker.pyint(min_value=1, max_value=10),
            time_zone=time_zone or cls._faker.timezone(),
            created_at=created,
            updated_at=updated_at or created,
            confirmed_at=confirmed_at or created,
            deleted_at=deleted_at,
            deletion_reason=deletion_reason,
        )

    @classmethod
    def fake_many(
        cls,
        count: int = 10,
        **overrides: object,
    ) -> list[Account]:
        fake = cast('Callable[..., Account]', cls.fake)
        return [fake(**overrides) for _ in range(count)]
