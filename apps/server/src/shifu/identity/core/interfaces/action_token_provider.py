from typing import Protocol


class ActionTokenProvider(Protocol):
    def generate(self) -> str:
        """Generate a URL-safe secret with at least 256 bits of entropy."""
        ...

    def hash(self, token: str) -> str:
        """Return the deterministic SHA-256 digest persisted by Identity."""
        ...
