from typing import Protocol


class IdentifierProvider(Protocol):
    def generate(self) -> str:
        """Generate a valid ULID string."""
        ...
