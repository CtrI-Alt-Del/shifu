from collections.abc import Sequence

from shifu.identity.core.interfaces import IdentityDatabase
from shifu.shared.core.domain.structures import ActiveAccount


class IdentityActiveAccountProvider:
    """Expose which accounts may still receive effects, and their time zone."""

    def __init__(self, database: IdentityDatabase) -> None:
        self._database = database

    def find_many_active(
        self,
        account_ids: Sequence[str],
    ) -> tuple[ActiveAccount, ...]:
        if not account_ids:
            return ()
        with self._database.transaction() as repositories:
            accounts = repositories.accounts.find_many_active_by_ids(account_ids)
        return tuple(
            ActiveAccount(account_id=account.id, time_zone=account.time_zone)
            for account in accounts
        )
