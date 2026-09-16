from typing import Protocol

from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import AccountActionTokenType


class AccountActionTokensRepository(Protocol):
    def find_by_hash(self, token_hash: str) -> AccountActionToken | None: ...

    def find_many_pending_by_account_id_and_type(
        self,
        account_id: str,
        token_type: AccountActionTokenType,
    ) -> list[AccountActionToken]: ...

    def add(self, token: AccountActionToken) -> None: ...

    def add_many(self, tokens: list[AccountActionToken]) -> None: ...

    def replace(self, token: AccountActionToken) -> None: ...

    def remove_all(self) -> None: ...
