from datetime import UTC, datetime
from typing import ClassVar

from shifu.fakers.shared.id_provider_faker import IdProviderFaker
from shifu.gamification.core.domain.entities import XpGrant
from shifu.gamification.core.domain.enums import XpSource
from shifu.gamification.core.domain.structures import XpOrigin


class XpGrantFaker:
    _id_provider: ClassVar[IdProviderFaker] = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        account_id: str | None = None,
        fact_id: str | None = None,
        amount: int = 6,
        origin: XpOrigin | None = None,
        occurred_at: datetime | None = None,
        granted_at: datetime | None = None,
    ) -> XpGrant:
        occurred = occurred_at or granted_at or datetime.now(UTC)
        return XpGrant.create(
            id=id if id is not None else cls._id_provider.generate(),
            account_id=account_id
            if account_id is not None
            else cls._id_provider.generate(),
            fact_id=fact_id if fact_id is not None else cls._id_provider.generate(),
            amount=amount,
            origin=origin
            if origin is not None
            else XpOrigin(
                source=XpSource.ACTIVITY,
                reference_id=cls._id_provider.generate(),
                label='Atividade de aprendizagem',
            ),
            occurred_at=occurred,
            granted_at=granted_at or occurred,
        )
