from typing import Protocol
from uuid import UUID


class AccountErasureTargetProvider(Protocol):
    def resolve_account_id(self, erasure_id: UUID) -> str | None:
        """Resolve an account only while its erasure is pending."""
        ...
