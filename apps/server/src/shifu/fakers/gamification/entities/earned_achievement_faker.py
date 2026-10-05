from datetime import UTC, datetime
from typing import ClassVar

from shifu.fakers.shared.id_provider_faker import IdProviderFaker
from shifu.gamification.core.domain.entities.earned_achievement import EarnedAchievement
from shifu.gamification.core.domain.enums.achievement_criterion_kind import (
    AchievementCriterionKind,
)
from shifu.gamification.core.domain.structures.achievement_criterion import (
    AchievementCriterion,
)


class EarnedAchievementFaker:
    _id_provider: ClassVar[IdProviderFaker] = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        account_id: str | None = None,
        achievement_id: str = 'primeiro-passo',
        achievement_name: str = 'Primeiro Passo',
        criterion: AchievementCriterion | None = None,
        xp_reward: int = 25,
        achieved_at: datetime | None = None,
        granted_at: datetime | None = None,
    ) -> EarnedAchievement:
        achieved = (
            achieved_at
            if achieved_at is not None
            else granted_at
            if granted_at is not None
            else datetime.now(UTC)
        )
        return EarnedAchievement.create(
            id=id if id is not None else cls._id_provider.generate(),
            account_id=account_id
            if account_id is not None
            else cls._id_provider.generate(),
            achievement_id=achievement_id,
            achievement_name=achievement_name,
            criterion=criterion
            if criterion is not None
            else AchievementCriterion.create(
                kind=AchievementCriterionKind.DIAGNOSTICS_COMPLETED, target=1
            ),
            xp_reward=xp_reward,
            achieved_at=achieved,
            granted_at=granted_at if granted_at is not None else achieved,
        )
