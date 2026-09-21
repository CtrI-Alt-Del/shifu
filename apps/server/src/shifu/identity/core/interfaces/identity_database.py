from contextlib import AbstractContextManager
from typing import Protocol

from shifu.identity.core.interfaces.account_action_tokens_repository import (
    AccountActionTokensRepository,
)
from shifu.identity.core.interfaces.accounts_repository import AccountsRepository
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.interfaces import EventsRepository


@structure
class IdentityDatabaseRepositories:
    accounts: AccountsRepository
    account_action_tokens: AccountActionTokensRepository
    events: EventsRepository


class IdentityDatabase(Protocol):
    def transaction(
        self,
    ) -> AbstractContextManager[IdentityDatabaseRepositories]:
        """Open the sole transaction boundary for one Identity operation."""
        ...
