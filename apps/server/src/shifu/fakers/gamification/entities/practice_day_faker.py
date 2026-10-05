from datetime import UTC, datetime
from typing import ClassVar

from shifu.fakers.shared.id_provider_faker import IdProviderFaker
from shifu.gamification.core.domain.entities import PracticeDay


class PracticeDayFaker:
    _id_provider: ClassVar[IdProviderFaker] = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        account_id: str | None = None,
        time_zone: str = 'America/Sao_Paulo',
        practiced_at: datetime | None = None,
        recognized_at: datetime | None = None,
    ) -> PracticeDay:
        practiced = practiced_at or recognized_at or datetime.now(UTC)
        return PracticeDay.create(
            id=id if id is not None else cls._id_provider.generate(),
            account_id=account_id
            if account_id is not None
            else cls._id_provider.generate(),
            time_zone=time_zone,
            practiced_at=practiced,
            recognized_at=recognized_at or practiced,
        )
