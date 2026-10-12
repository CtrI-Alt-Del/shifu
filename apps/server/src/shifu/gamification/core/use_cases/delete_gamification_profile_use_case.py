from shifu.gamification.core.interfaces import GamificationDatabase


class DeleteGamificationProfileUseCase:
    """Purge every Gamification row for one account, on account deletion.

    No-op if the account never had a profile (already purged, or never
    activated).
    """

    def __init__(self, database: GamificationDatabase) -> None:
        self._database = database

    def execute(self, account_id: str) -> None:
        with self._database.transaction() as repositories:
            profile = repositories.profiles.find_by_account_id(account_id)
            if profile is None:
                return
            repositories.profiles.remove(profile)
            repositories.xp_grants.remove_many_by_account_id(account_id)
            repositories.earned_achievements.remove_many_by_account_id(account_id)
            repositories.rewarded_milestones.remove_many_by_account_id(account_id)
