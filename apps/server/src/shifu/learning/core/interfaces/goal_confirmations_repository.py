from typing import Protocol

from shifu.learning.core.domain.structures import GoalConfirmation


class GoalConfirmationsRepository(Protocol):
    def lock(self, account_id: str, confirmation_key: str) -> None:
        """Serialize concurrent deliveries of one confirmation inside the transaction."""
        ...

    def find(
        self, account_id: str, confirmation_key: str
    ) -> GoalConfirmation | None: ...

    def add(self, confirmation: GoalConfirmation) -> None: ...
