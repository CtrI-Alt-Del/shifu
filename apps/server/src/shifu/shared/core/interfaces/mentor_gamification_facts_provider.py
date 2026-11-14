from typing import Protocol


class MentorGamificationFactsProvider(Protocol):
    def read(self, account_id: str) -> tuple[tuple[str, str], ...]: ...
