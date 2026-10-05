from datetime import UTC, datetime
from typing import ClassVar

from shifu.fakers.shared.id_provider_faker import IdProviderFaker
from shifu.gamification.core.domain.entities import RewardedMilestone
from shifu.gamification.core.domain.enums import MilestoneKind


class RewardedMilestoneFaker:
    _id_provider: ClassVar[IdProviderFaker] = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        account_id: str | None = None,
        fact_id: str | None = None,
        kind: MilestoneKind = MilestoneKind.DIAGNOSIS,
        subject_id: str | None = None,
        xp_grant_id: str | None = None,
        occurred_at: datetime | None = None,
        rewarded_at: datetime | None = None,
    ) -> RewardedMilestone:
        occurred = occurred_at or rewarded_at or datetime.now(UTC)
        return RewardedMilestone.create(
            id=id if id is not None else cls._id_provider.generate(),
            account_id=account_id
            if account_id is not None
            else cls._id_provider.generate(),
            fact_id=fact_id if fact_id is not None else cls._id_provider.generate(),
            kind=kind,
            subject_id=subject_id
            if subject_id is not None
            else cls._id_provider.generate(),
            xp_grant_id=xp_grant_id
            if xp_grant_id is not None
            else cls._id_provider.generate(),
            occurred_at=occurred,
            rewarded_at=rewarded_at or occurred,
        )
