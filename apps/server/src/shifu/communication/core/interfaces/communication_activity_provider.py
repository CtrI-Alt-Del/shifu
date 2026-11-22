from contextlib import AbstractContextManager
from typing import Protocol


class CommunicationActivityProvider(Protocol):
    def activity(self, account_id: str) -> AbstractContextManager[None]:
        """Admit delivery for active or confirmation-pending accounts only."""
        ...
