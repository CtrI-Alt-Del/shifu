from typing import Protocol

from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import AccountActionTokenType


class AccountActionTokensRepository(Protocol):
    def find_by_hash(self, token_hash: str) -> AccountActionToken | None:
        """Find and lock a token by its persisted hash in the caller transaction."""
        ...

    def find_many_pending_by_account_id_and_type(
        self,
        account_id: str,
        token_type: AccountActionTokenType,
    ) -> list[AccountActionToken]: ...

    def add(self, token: AccountActionToken) -> None: ...

    def add_many(self, tokens: list[AccountActionToken]) -> None: ...

    def update(self, token: AccountActionToken) -> None: ...

    def remove_all(self) -> None: ...


class ConfirmationAccountActionTokensRepository(
    AccountActionTokensRepository,
    Protocol,
):
    """Extended lock-aware token contract for registration confirmation flows."""

    def find_by_id(self, identity_confirmation_id: str) -> AccountActionToken | None:
        """Find and lock a confirmation correlation in the caller transaction."""
        ...

    def find_by_pending_handle_hash(
        self,
        pending_handle_hash: str,
    ) -> AccountActionToken | None:
        """Resolve a pending handle without exposing account or e-mail identity."""
        ...

    def find_latest_by_account_id_and_type(
        self,
        account_id: str,
        token_type: AccountActionTokenType,
    ) -> AccountActionToken | None:
        """Find and lock the latest issued token for cooldown decisions."""
        ...

    def find_many_by_account_id_and_type(
        self,
        account_id: str,
        token_type: AccountActionTokenType,
    ) -> list[AccountActionToken]:
        """Load all token states needed for atomic cancellation or expiry."""
        ...
