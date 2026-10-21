from shifu.gamification.core.domain.entities import GamificationProfile
from shifu.gamification.core.domain.structures import PracticeStreak
from shifu.gamification.database.sqlalchemy.models import GamificationProfileModel


class GamificationProfileMapper:
    @staticmethod
    def to_domain(model: GamificationProfileModel) -> GamificationProfile:
        return GamificationProfile(
            id=model.id,
            account_id=model.account_id,
            total_xp=model.total_xp,
            level=model.level,
            streak=PracticeStreak(
                current=model.streak_current,
                longest=model.streak_longest,
                latest_practice_date=model.streak_latest_practice_date,
            ),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(profile: GamificationProfile) -> GamificationProfileModel:
        return GamificationProfileModel(
            id=profile.id,
            account_id=profile.account_id,
            total_xp=profile.total_xp,
            level=profile.level,
            streak_current=profile.streak.current,
            streak_longest=profile.streak.longest,
            streak_latest_practice_date=profile.streak.latest_practice_date,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
