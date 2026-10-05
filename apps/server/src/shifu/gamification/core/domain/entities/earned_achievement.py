from datetime import datetime

from shifu.gamification.core.domain.errors import InvalidGamificationError
from shifu.gamification.core.domain.structures.achievement_criterion import (
    AchievementCriterion,
)
from shifu.shared.core.domain.entities import frozen_entity
from shifu.shared.core.domain.structures import (
    BoundedInteger,
    ChronologicalPeriod,
    NonEmptyText,
)


@frozen_entity
class EarnedAchievement:
    id: str
    account_id: str
    achievement_id: str
    achievement_name: str
    criterion: AchievementCriterion
    xp_reward: int
    achieved_at: datetime
    granted_at: datetime

    def __post_init__(self) -> None:
        NonEmptyText.create(self.id, error_type=InvalidGamificationError)
        NonEmptyText.create(self.account_id, error_type=InvalidGamificationError)
        NonEmptyText.create(self.achievement_id, error_type=InvalidGamificationError)
        NonEmptyText.create(self.achievement_name, error_type=InvalidGamificationError)
        BoundedInteger.create(
            self.xp_reward, minimum=1, error_type=InvalidGamificationError
        )
        ChronologicalPeriod.create(
            self.achieved_at, self.granted_at, error_type=InvalidGamificationError
        )
        if type(self.criterion) is not AchievementCriterion:
            raise InvalidGamificationError

    @classmethod
    def create(
        cls,
        *,
        id: str,
        account_id: str,
        achievement_id: str,
        achievement_name: str,
        criterion: AchievementCriterion,
        xp_reward: int,
        achieved_at: datetime,
        granted_at: datetime,
    ) -> 'EarnedAchievement':
        return cls(
            id=NonEmptyText.create(id, error_type=InvalidGamificationError).value,
            account_id=NonEmptyText.create(
                account_id, error_type=InvalidGamificationError
            ).value,
            achievement_id=NonEmptyText.create(
                achievement_id, error_type=InvalidGamificationError
            ).value,
            achievement_name=NonEmptyText.create(
                achievement_name, error_type=InvalidGamificationError
            ).value,
            criterion=criterion,
            xp_reward=xp_reward,
            achieved_at=achieved_at,
            granted_at=granted_at,
        )
