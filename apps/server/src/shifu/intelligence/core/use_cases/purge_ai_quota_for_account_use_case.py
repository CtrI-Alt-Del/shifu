from shifu.intelligence.core.interfaces import IntelligenceDatabase


class PurgeAiQuotaForAccountUseCase:
    def __init__(self, database: IntelligenceDatabase) -> None:
        self._database: IntelligenceDatabase = database

    def execute(self, account_id: str) -> int:
        """Remove every quota record of the account; repeated calls return 0."""
        with self._database.transaction() as repositories:
            # A charge or refund that already holds the month finishes first; one
            # that waits finds the month gone and does nothing.
            repositories.ai_quota_months.lock_by_account_id(account_id)
            charges = repositories.ai_quota_charges.remove_by_account_id(account_id)
            months = repositories.ai_quota_months.remove_by_account_id(account_id)
        return charges + months
