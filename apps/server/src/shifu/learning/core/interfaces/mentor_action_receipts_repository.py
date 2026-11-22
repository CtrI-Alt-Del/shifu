from typing import Protocol

from shifu.learning.core.domain.entities import MentorActionReceipt


class MentorActionReceiptsRepository(Protocol):
    def find_by_confirmation_id(
        self,
        account_id: str,
        confirmation_id: str,
    ) -> MentorActionReceipt | None: ...

    def try_add(self, receipt: MentorActionReceipt) -> bool:
        """Insert the receipt, returning False when the (account, confirmation) pair exists."""
        ...

    def remove_by_account_id(self, account_id: str) -> None:
        """Remove the account's operation receipts."""
        ...
