from datetime import UTC, datetime
from typing import ClassVar

from shifu.fakers.shared.id_provider_faker import IdProviderFaker
from shifu.gamification.core.domain.entities import ActivityXpBalance


class ActivityXpBalanceFaker:
    _id_provider: ClassVar[IdProviderFaker] = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        account_id: str | None = None,
        activity_id: str | None = None,
        maximum_xp: int = 10,
        granted_xp: int = 0,
        updated_at: datetime | None = None,
    ) -> ActivityXpBalance:
        return ActivityXpBalance(
            id=id if id is not None else cls._id_provider.generate(),
            account_id=account_id
            if account_id is not None
            else cls._id_provider.generate(),
            activity_id=activity_id
            if activity_id is not None
            else cls._id_provider.generate(),
            maximum_xp=maximum_xp,
            granted_xp=granted_xp,
            updated_at=updated_at or datetime.now(UTC),
        )
