from typing import cast

from shifu.gamification.core.domain.entities import EarnedAchievement
from shifu.gamification.core.domain.structures import AchievementCriterion
from shifu.gamification.database.sqlalchemy.models import EarnedAchievementModel
from shifu.shared.database.sqlalchemy.serialization import Serialization


class EarnedAchievementMapper:
    @staticmethod
    def to_domain(model: EarnedAchievementModel) -> EarnedAchievement:
        return EarnedAchievement(
            id=model.id,
            account_id=model.account_id,
            achievement_id=model.achievement_id,
            achievement_name=model.achievement_name,
            criterion=cast(
                'AchievementCriterion',
                Serialization.deserialize_value(
                    model.criterion, AchievementCriterion
                ),
            ),
            xp_reward=model.xp_reward,
            achieved_at=model.achieved_at,
            granted_at=model.granted_at,
        )

    @staticmethod
    def to_model(earned: EarnedAchievement) -> EarnedAchievementModel:
        return EarnedAchievementModel(
            id=earned.id,
            account_id=earned.account_id,
            achievement_id=earned.achievement_id,
            achievement_name=earned.achievement_name,
            criterion=Serialization.serialize_value(earned.criterion),
            xp_reward=earned.xp_reward,
            achieved_at=earned.achieved_at,
            granted_at=earned.granted_at,
        )
