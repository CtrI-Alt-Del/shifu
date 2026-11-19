from typing import Protocol

from shifu.intelligence.core.domain.entities.ai_quota_charge import AiQuotaCharge
from shifu.intelligence.core.domain.enums.ai_quota_request_kind import (
    AiQuotaRequestKind,
)


class AiQuotaChargesRepository(Protocol):
    def add(self, charge: AiQuotaCharge) -> None: ...

    def find(self, kind: AiQuotaRequestKind, request_id: str) -> AiQuotaCharge | None:
        """Read without locking, to learn the month before it is locked."""
        ...

    def find_for_update(
        self, kind: AiQuotaRequestKind, request_id: str
    ) -> AiQuotaCharge | None: ...

    def update(self, charge: AiQuotaCharge) -> None: ...

    def remove_by_account_id(self, account_id: str) -> int: ...
