from shifu.gamification.core.domain.entities import (
    EarnedAchievement,
    GamificationProfile,
    PracticeDay,
    XpGrant,
)
from shifu.gamification.core.interfaces import (
    ActivityXpBalancesRepository,
    ActivityXpRecognitionsRepository,
    EarnedAchievementsRepository,
    GamificationProfilesRepository,
    PracticeDaysRepository,
    RewardedMilestonesRepository,
    XpGrantsRepository,
)


class GamificationSeeder:
    def __init__(
        self,
        profiles_repository: GamificationProfilesRepository,
        xp_grants_repository: XpGrantsRepository,
        earned_achievements_repository: EarnedAchievementsRepository,
        rewarded_milestones_repository: RewardedMilestonesRepository,
        practice_days_repository: PracticeDaysRepository,
        activity_xp_balances_repository: ActivityXpBalancesRepository,
        activity_xp_recognitions_repository: ActivityXpRecognitionsRepository,
    ) -> None:
        self._profiles_repository: GamificationProfilesRepository = profiles_repository
        self._xp_grants_repository: XpGrantsRepository = xp_grants_repository
        self._earned_achievements_repository: EarnedAchievementsRepository = (
            earned_achievements_repository
        )
        self._rewarded_milestones_repository: RewardedMilestonesRepository = (
            rewarded_milestones_repository
        )
        self._practice_days_repository: PracticeDaysRepository = (
            practice_days_repository
        )
        self._activity_xp_balances_repository: ActivityXpBalancesRepository = (
            activity_xp_balances_repository
        )
        self._activity_xp_recognitions_repository: ActivityXpRecognitionsRepository = (
            activity_xp_recognitions_repository
        )

    def clear(self, account_ids: list[str]) -> None:
        # Gamification rows carry no foreign key to accounts, so clearing
        # Identity alone would leave the previous seed's state behind.
        for account_id in account_ids:
            profile = self._profiles_repository.find_by_account_id(account_id)
            if profile is not None:
                self._profiles_repository.remove(profile)
            self._xp_grants_repository.remove_many_by_account_id(account_id)
            self._earned_achievements_repository.remove_many_by_account_id(account_id)
            self._rewarded_milestones_repository.remove_many_by_account_id(account_id)
            self._practice_days_repository.remove_many_by_account_id(account_id)
            self._activity_xp_balances_repository.remove_many_by_account_id(account_id)
            self._activity_xp_recognitions_repository.remove_many_by_account_id(
                account_id
            )

    def run(
        self,
        profiles: list[GamificationProfile],
        practice_days: list[PracticeDay],
        earned_achievements: list[EarnedAchievement],
        xp_grants: list[XpGrant],
    ) -> None:
        for profile in profiles:
            self._profiles_repository.add(profile)
        for practice_day in practice_days:
            self._practice_days_repository.try_add(practice_day)
        for earned_achievement in earned_achievements:
            self._earned_achievements_repository.try_add(earned_achievement)
        for xp_grant in xp_grants:
            self._xp_grants_repository.add(xp_grant)
