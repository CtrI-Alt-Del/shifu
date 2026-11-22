from collections.abc import Sequence
from typing import Protocol

from shifu.shared.core.domain.structures import ActiveAccount


class ActiveAccountProvider(Protocol):
    def find_many_active(
        self,
        account_ids: Sequence[str],
    ) -> tuple[ActiveAccount, ...]:
        """Return only accounts that are still active, with their time zone.

        Pending, expired and deleted accounts are never returned. An empty input
        returns an empty tuple without querying.
        """
        ...
