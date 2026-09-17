from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

from faker import Faker

from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
)
from shifu.fakers.shared.id_provider_faker import IdProviderFaker

if TYPE_CHECKING:
    from collections.abc import Callable


class AccountActionTokenFaker:
    _faker: Faker = Faker('pt_BR')
    _id_provider: IdProviderFaker = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        account_id: str | None = None,
        type: AccountActionTokenType = AccountActionTokenType.EMAIL_CONFIRMATION,
        status: AccountActionTokenStatus = AccountActionTokenStatus.PENDING,
        token_hash: str | None = None,
        issued_at: datetime | None = None,
        expires_at: datetime | None = None,
        updated_at: datetime | None = None,
        used_at: datetime | None = None,
        invalidated_at: datetime | None = None,
    ) -> AccountActionToken:
        issued = issued_at or cls._faker.date_time(tzinfo=UTC)
        return AccountActionToken(
            id=id or cls._id_provider.generate(),
            account_id=account_id or cls._id_provider.generate(),
            type=type,
            status=status,
            token_hash=token_hash or cls._faker.sha256(raw_output=False),
            issued_at=issued,
            expires_at=expires_at or issued + timedelta(hours=24),
            updated_at=updated_at or issued,
            used_at=used_at,
            invalidated_at=invalidated_at,
        )

    @classmethod
    def fake_many(
        cls,
        count: int = 10,
        **overrides: object,
    ) -> list[AccountActionToken]:
        fake = cast('Callable[..., AccountActionToken]', cls.fake)
        return [fake(**overrides) for _ in range(count)]
