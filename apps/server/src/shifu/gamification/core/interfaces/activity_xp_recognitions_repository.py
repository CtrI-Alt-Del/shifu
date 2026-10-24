from typing import Protocol

from shifu.gamification.core.domain.entities import ActivityXpRecognition


class ActivityXpRecognitionsRepository(Protocol):
    def try_add(self, recognition: ActivityXpRecognition) -> bool:
        """Insert one recognition; return False when that attempt was already processed."""
        ...

    def find_by_account_id_and_attempt_id(
        self, account_id: str, attempt_id: str
    ) -> ActivityXpRecognition | None: ...

    def remove_many_by_account_id(self, account_id: str) -> None:
        """Delete every ActivityXpRecognition row for one account (account-deletion purge)."""
        ...
