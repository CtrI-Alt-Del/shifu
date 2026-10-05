from datetime import UTC, datetime
from typing import ClassVar

from shifu.fakers.shared.id_provider_faker import IdProviderFaker
from shifu.gamification.core.domain.entities import RewardFeedback


class RewardFeedbackFaker:
    _id_provider: ClassVar[IdProviderFaker] = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        account_id: str | None = None,
        fact_id: str | None = None,
        xp_grant_ids: tuple[str, ...] | None = None,
        earned_achievement_ids: tuple[str, ...] = (),
        previous_level: int = 1,
        new_level: int = 1,
        created_at: datetime | None = None,
        seen_at: datetime | None = None,
    ) -> RewardFeedback:
        created = created_at or seen_at or datetime.now(UTC)
        return RewardFeedback(
            id=id if id is not None else cls._id_provider.generate(),
            account_id=account_id
            if account_id is not None
            else cls._id_provider.generate(),
            fact_id=fact_id if fact_id is not None else cls._id_provider.generate(),
            xp_grant_ids=xp_grant_ids
            if xp_grant_ids is not None
            else (cls._id_provider.generate(),),
            earned_achievement_ids=earned_achievement_ids,
            previous_level=previous_level,
            new_level=new_level,
            created_at=created,
            seen_at=seen_at,
        )
