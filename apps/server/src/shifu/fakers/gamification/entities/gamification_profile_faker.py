from datetime import UTC, datetime
from typing import ClassVar

from shifu.fakers.shared.id_provider_faker import IdProviderFaker
from shifu.gamification.core.domain.entities import GamificationProfile
from shifu.gamification.core.domain.structures import PracticeStreak


class GamificationProfileFaker:
    _id_provider: ClassVar[IdProviderFaker] = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        account_id: str | None = None,
        total_xp: int = 0,
        level: int | None = None,
        streak: PracticeStreak | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> GamificationProfile:
        created = created_at or updated_at or datetime.now(UTC)
        return GamificationProfile(
            id=id if id is not None else cls._id_provider.generate(),
            account_id=account_id
            if account_id is not None
            else cls._id_provider.generate(),
            total_xp=total_xp,
            level=level
            if level is not None
            else GamificationProfile.level_for_xp(total_xp),
            streak=streak if streak is not None else PracticeStreak(),
            created_at=created,
            updated_at=updated_at or created,
        )
