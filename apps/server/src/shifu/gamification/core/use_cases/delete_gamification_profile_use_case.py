from shifu.gamification.core.interfaces import GamificationDatabase


class DeleteGamificationProfileUseCase:
    """Purge every Gamification row for one account, on account deletion.

    Profile removal is skipped when absent; owner rows are always purged.
    """

    def __init__(self, database: GamificationDatabase) -> None:
        self._database = database

    def execute(self, account_id: str) -> None:
        with self._database.transaction() as repositories:
            profile = repositories.profiles.find_by_account_id_for_update(account_id)
            if profile is not None:
                repositories.profiles.remove(profile)
            repositories.xp_grants.remove_many_by_account_id(account_id)
            repositories.earned_achievements.remove_many_by_account_id(account_id)
            repositories.rewarded_milestones.remove_many_by_account_id(account_id)
            repositories.practice_days.remove_many_by_account_id(account_id)
            repositories.activity_xp_balances.remove_many_by_account_id(account_id)
            repositories.activity_xp_recognitions.remove_many_by_account_id(account_id)
