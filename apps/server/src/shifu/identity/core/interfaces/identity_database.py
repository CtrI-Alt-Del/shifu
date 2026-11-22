from contextlib import AbstractContextManager
from typing import Protocol

from shifu.identity.core.interfaces.account_action_tokens_repository import (
    AccountActionTokensRepository,
)
from shifu.identity.core.interfaces.account_browser_capabilities_repository import (
    AccountBrowserCapabilitiesRepository,
)
from shifu.identity.core.interfaces.account_external_effect_receipts_repository import (
    AccountExternalEffectReceiptsRepository,
)
from shifu.identity.core.interfaces.account_erasure_repository import (
    AccountErasureRepository,
)
from shifu.identity.core.interfaces.accounts_repository import AccountsRepository
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.interfaces import EventsRepository


@structure
class IdentityDatabaseRepositories:
    accounts: AccountsRepository
    account_action_tokens: AccountActionTokensRepository
    account_browser_capabilities: AccountBrowserCapabilitiesRepository
    external_effect_receipts: AccountExternalEffectReceiptsRepository
    account_erasures: AccountErasureRepository
    events: EventsRepository


class IdentityDatabase(Protocol):
    def transaction(
        self,
    ) -> AbstractContextManager[IdentityDatabaseRepositories]:
        """Open the sole transaction boundary for one Identity operation."""
        ...

    def account_closure_transaction(
        self, account_id: str
    ) -> AbstractContextManager[IdentityDatabaseRepositories]:
        """Open a transaction under the account's exclusive activity lock."""
        ...
