from shifu.identity.core.interfaces import IdentityDatabase


class IdentityAccountTimeZoneProvider:
    """Expose an account's current time zone to other modules, nothing else."""

    def __init__(self, database: IdentityDatabase) -> None:
        self._database = database

    def find_time_zone(self, account_id: str) -> str | None:
        with self._database.transaction() as repositories:
            account = repositories.accounts.find_by_id(account_id)
            return account.time_zone if account is not None else None
