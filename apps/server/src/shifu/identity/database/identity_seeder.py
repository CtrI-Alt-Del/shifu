from shifu.identity.core.domain.entities import Account, AccountActionToken
from shifu.identity.core.interfaces import (
    AccountActionTokensRepository,
    AccountsRepository,
)


class IdentitySeeder:
    def __init__(
        self,
        accounts_repository: AccountsRepository,
        account_action_tokens_repository: AccountActionTokensRepository,
    ) -> None:
        self._accounts_repository: AccountsRepository = accounts_repository
        self._account_action_tokens_repository: AccountActionTokensRepository = (
            account_action_tokens_repository
        )

    def clear(self) -> None:
        self._account_action_tokens_repository.remove_all()
        self._accounts_repository.remove_all()

    def run(
        self,
        accounts: list[Account],
        account_action_tokens: list[AccountActionToken] | None = None,
    ) -> None:
        self._accounts_repository.add_many(accounts)
        self._account_action_tokens_repository.add_many(account_action_tokens or [])
